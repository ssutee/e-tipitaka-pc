#-*- coding:utf-8 -*-

import os
import shutil
import tempfile
import threading
import unittest

import requests

from account.client import AccountError, RateLimited
from account.pairing import PairingSession, DENIED, EXPIRED, FAILED
from account.tokenstore import TokenStore


URL = 'https://data.etipitaka.example/desktop/?code=ABCD-2345'

PENDING = {'status': 'pending'}
APPROVED = {'status': 'approved', 'key': 'tok-alice', 'username': 'alice'}
REFUSED = {'status': 'denied'}


def _begin(interval=5, expires_in=600):
    return {'device_code': 'dev-secret', 'user_code': 'ABCD-2345',
            'verification_url': URL, 'interval': interval,
            'expires_in': expires_in}


class FakeClient(object):
    """Scripted stand-in for AccountClient. Each poll takes the next item:
    a dict is returned, an exception instance is raised."""

    def __init__(self, begin, polls):
        self._begin = begin
        self._polls = list(polls)
        self.poll_calls = []

    def desktop_begin(self):
        if isinstance(self._begin, Exception):
            raise self._begin
        return dict(self._begin)

    def desktop_poll(self, device_code):
        self.poll_calls.append(device_code)
        if not self._polls:
            raise AssertionError('polled more often than the test scripted')
        item = self._polls.pop(0)
        if isinstance(item, Exception):
            raise item
        return dict(item)


class FakeClock(object):
    """Time that moves only when the session sleeps, so a ten-minute pairing
    runs in microseconds. `on_sleep(n)` is called after the n-th sleep."""

    def __init__(self):
        self.t = 0.0
        self.sleeps = []
        self.on_sleep = None

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds
        if self.on_sleep is not None:
            self.on_sleep(len(self.sleeps))


class Recorder(object):

    def __init__(self):
        self.events = []

    def on_code(self, user_code, url):
        self.events.append(('code', user_code, url))

    def on_done(self, username):
        self.events.append(('done', username))

    def on_error(self, reason, err):
        self.events.append(('error', reason, err))


class TestPairingSession(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = TokenStore(os.path.join(self.tmpdir, 'account.cfg'))
        self.clock = FakeClock()
        self.rec = Recorder()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _session(self, client, dispatch=None):
        return PairingSession(
            client, self.store,
            on_code=self.rec.on_code, on_done=self.rec.on_done,
            on_error=self.rec.on_error,
            dispatch=dispatch or (lambda fn: fn()),
            sleep=self.clock.sleep, now=self.clock.now)

    def _failed(self):
        """The error carried by the final event, which must be FAILED."""
        last = self.rec.events[-1]
        self.assertEqual(('error', FAILED), last[:2])
        return last[2]

    # --- happy path ------------------------------------------------------

    def testApprovalAfterPendingStoresTheToken(self):
        client = FakeClient(_begin(), [PENDING, PENDING, APPROVED])
        self._session(client).run()
        self.assertEqual([('code', 'ABCD-2345', URL), ('done', 'alice')],
                         self.rec.events)
        self.assertEqual(['dev-secret'] * 3, client.poll_calls)
        self.assertEqual([5, 5, 5], self.clock.sleeps)
        data = self.store.get()
        self.assertEqual('tok-alice', data['token'])
        self.assertEqual('alice', data['username'])

    def testApprovalReplacesThePreviousAccount(self):
        # Same guarantee as AccountClient.login(): clear() before set(), or
        # the previous account's last_upload leaks into the new session.
        self.store.set('tok-bob', 'bob')
        self.store.set_last_upload('2026-01-01T00:00:00')
        client = FakeClient(_begin(), [APPROVED])
        self._session(client).run()
        data = self.store.get()
        self.assertEqual('tok-alice', data['token'])
        self.assertEqual('alice', data['username'])
        self.assertNotIn('last_upload', data)

    def testTheTokenIsStoredBeforeOnDoneRuns(self):
        # The dialog redraws from the store the moment on_done runs.
        seen = []
        self.rec.on_done = lambda username: seen.append(
            (self.store.get() or {}).get('token'))
        self._session(FakeClient(_begin(), [APPROVED])).run()
        self.assertEqual(['tok-alice'], seen)

    def testAFailedTokenWriteStillEndsTheSession(self):
        # _approved runs on the UI thread, outside run()'s catch-all, so it
        # must end the session itself. Hence a queued dispatch, as in the
        # app: a synchronous one would let run() catch the error and hide
        # the bug.
        def full_disk(token, username):
            raise OSError(28, 'No space left on device')
        self.store.set = full_disk
        queue = []
        self._session(FakeClient(_begin(), [APPROVED]),
                      dispatch=queue.append).run()
        for fn in queue:
            fn()
        err = self._failed()
        self.assertEqual(2, len(self.rec.events))   # the code, then this
        self.assertIn('No space left on device', err.message)
        self.assertNotIn('tok-alice', err.message)
        self.assertFalse(self.store.is_logged_in())

    def testFollowsTheServersIntervalAndExpiry(self):
        client = FakeClient(_begin(interval=7, expires_in=20),
                            [PENDING, PENDING])
        self._session(client).run()
        # t=7 poll, t=14 poll, then sleep only the 6s left and give up.
        self.assertEqual([7, 7, 6], self.clock.sleeps)
        self.assertEqual(2, len(client.poll_calls))
        self.assertEqual(('error', EXPIRED, None), self.rec.events[-1])
        self.assertFalse(self.store.is_logged_in())

    def testFallsBackToDefaultsWhenServerValuesAreUnusable(self):
        for interval, expires_in in (('soon', 0), (None, -1), (-5, None)):
            case = (interval, expires_in)
            self.clock, self.rec = FakeClock(), Recorder()
            client = FakeClient(_begin(interval, expires_in), [PENDING] * 200)
            self._session(client).run()
            self.assertEqual(5, self.clock.sleeps[0], case)
            self.assertEqual(600, sum(self.clock.sleeps), case)
            self.assertEqual(119, len(client.poll_calls), case)
            self.assertEqual(('error', EXPIRED, None), self.rec.events[-1],
                             case)

    def testAnUnexpectedExceptionStillEndsTheSession(self):
        # Every session must end in exactly one callback; a worker that dies
        # silently would leave the dialog pulsing forever.
        client = FakeClient(_begin(), [RuntimeError('bug')])
        self._session(client).run()
        err = self._failed()
        self.assertEqual(-1, err.status)
        self.assertIn('bug', err.message)

    def testAnUnrecognisedStatusFailsLoudly(self):
        client = FakeClient(_begin(), [{'status': 'weird'}])
        self._session(client).run()
        self.assertIn('weird', self._failed().message)
        self.assertEqual(1, len(client.poll_calls))

    def testApprovedWithoutUsernameFailsWithoutLeakingTheToken(self):
        client = FakeClient(_begin(),
                            [{'status': 'approved', 'key': 'tok-secret'}])
        self._session(client).run()
        err = self._failed()
        # 200 is _unexpected's status. run()'s catch-all would say -1, which
        # would mean the missing username was never checked.
        self.assertEqual(200, err.status)
        # The message is shown to the user, so it must never carry the key.
        self.assertNotIn('tok-secret', err.message)
        self.assertFalse(self.store.is_logged_in())

    # --- cancellation ----------------------------------------------------

    def testCancelStopsPollingAndFiresNothing(self):
        client = FakeClient(_begin(), [PENDING, PENDING, APPROVED])
        session = self._session(client)
        self.clock.on_sleep = lambda n: session.cancel() if n == 2 else None
        session.run()
        self.assertEqual(1, len(client.poll_calls))
        self.assertEqual([('code', 'ABCD-2345', URL)], self.rec.events)
        self.assertFalse(self.store.is_logged_in())

    def testCancelDropsACallbackAlreadyQueued(self):
        # wx.CallAfter defers: an approval can be queued on the UI thread a
        # moment before the user presses Cancel. It must not then run.
        queue = []
        client = FakeClient(_begin(), [APPROVED])
        session = self._session(client, dispatch=queue.append)
        session.run()
        self.assertEqual(2, len(queue))     # on_code, then the approval
        queue[0]()                          # the code reaches the UI ...
        session.cancel()                    # ... the user cancels ...
        for fn in queue[1:]:                # ... before the approval runs
            fn()
        self.assertEqual([('code', 'ABCD-2345', URL)], self.rec.events)
        self.assertFalse(self.store.is_logged_in())

    def testCancelWakesTheDefaultSleepPromptly(self):
        # The real default sleep, not the fake clock: cancel() must wake the
        # worker at once, not leave it blocked for a 60-second interval.
        client = FakeClient(_begin(interval=60), [])
        coded = threading.Event()
        session = PairingSession(
            client, self.store,
            on_code=lambda *a: coded.set(),
            on_done=self.rec.on_done, on_error=self.rec.on_error,
            dispatch=lambda fn: fn())
        worker = threading.Thread(target=session.run, daemon=True)
        worker.start()
        self.assertTrue(coded.wait(5))
        session.cancel()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], client.poll_calls)
        self.assertEqual([], self.rec.events)

    def testStartRunsTheHandshakeOnAWorkerThread(self):
        finished = threading.Event()
        threads = []

        def dispatch(fn):
            threads.append(threading.current_thread())
            fn()
            if self.rec.events and self.rec.events[-1][0] in ('done', 'error'):
                finished.set()

        client = FakeClient(_begin(), [APPROVED])
        self._session(client, dispatch=dispatch).start()
        self.assertTrue(finished.wait(5))
        self.assertEqual(('done', 'alice'), self.rec.events[-1])
        self.assertNotIn(threading.main_thread(), threads)


def suite():
    s = unittest.TestSuite()
    for name in ['testApprovalAfterPendingStoresTheToken',
                 'testApprovalReplacesThePreviousAccount',
                 'testTheTokenIsStoredBeforeOnDoneRuns',
                 'testAFailedTokenWriteStillEndsTheSession',
                 'testFollowsTheServersIntervalAndExpiry',
                 'testFallsBackToDefaultsWhenServerValuesAreUnusable',
                 'testAnUnexpectedExceptionStillEndsTheSession',
                 'testAnUnrecognisedStatusFailsLoudly',
                 'testApprovedWithoutUsernameFailsWithoutLeakingTheToken',
                 'testCancelStopsPollingAndFiresNothing',
                 'testCancelDropsACallbackAlreadyQueued',
                 'testCancelWakesTheDefaultSleepPromptly',
                 'testStartRunsTheHandshakeOnAWorkerThread']:
        s.addTest(TestPairingSession(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

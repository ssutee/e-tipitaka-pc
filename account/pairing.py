#-*- coding:utf-8 -*-
"""Desktop passkey sign-in: start a pairing, then poll until the user decides.

The passkey ceremony happens in the system browser, on data.etipitaka.com.
It cannot happen here: WebAuthn origins are minted by the browser or the OS,
and the server accepts exactly one, so a Python process cannot produce a
credential it would take. This module runs only the handshake around that
ceremony -- begin, show a code, poll -- and ends with the same DRF token a
password sign-in gets, so the rest of the account code is unchanged.

It imports no wx, like account/client.py. Every callback goes through the
injected `dispatch` (wx.CallAfter in the app), which is what lets the tests
drive the whole state machine synchronously with a fake clock.
"""
import threading
import time

from account.client import AccountError

# Why a session ended without a token; passed to on_error. The dialog words
# each case itself, so this module holds no user-facing text.
DENIED = 'denied'    # the user pressed No in the browser
EXPIRED = 'expired'  # the pairing ran out, or the server no longer knows it
FAILED = 'failed'    # begin failed, or polling kept failing; see the error

DEFAULT_INTERVAL = 5      # seconds; used when the server's value is unusable
DEFAULT_EXPIRES_IN = 600


def _seconds(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class PairingSession(object):
    """One sign-in attempt. Callbacks, each run through `dispatch`:

        on_code(user_code, verification_url)   once, after begin succeeds
        on_done(username)                      the token has been stored
        on_error(reason, err)                  DENIED, EXPIRED or FAILED

    Exactly one of on_done / on_error ends every session -- unless cancel()
    comes first, in which case nothing more fires at all.
    """

    def __init__(self, client, store, on_code, on_done, on_error, dispatch,
                 sleep=None, now=time.monotonic):
        self._client = client
        self._store = store
        self._on_code = on_code
        self._on_done = on_done
        self._on_error = on_error
        self._dispatch = dispatch
        self._cancelled = threading.Event()
        # Waiting on the event, not time.sleep, so cancel() wakes the worker
        # at once instead of leaving it asleep for a whole interval.
        self._sleep = sleep if sleep is not None else self._cancelled.wait
        self._now = now

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def cancel(self):
        """Stop. Afterwards no callback fires -- including one already
        queued on the UI thread -- and no token is stored. The server is not
        told: an approval made in the browser after this expires unpolled."""
        self._cancelled.set()

    def run(self):
        """The whole handshake, synchronously. start() runs this on a worker
        thread; the tests call it directly."""
        try:
            self._handshake()
        except Exception as e:
            # Never leave the dialog pulsing at a thread that has died.
            self._deliver(self._on_error, FAILED, AccountError(-1, str(e)))

    def _handshake(self):
        pairing = self._client.desktop_begin()
        interval = _seconds(pairing.get('interval'), DEFAULT_INTERVAL)
        deadline = self._now() + _seconds(pairing.get('expires_in'),
                                          DEFAULT_EXPIRES_IN)
        self._deliver(self._on_code, pairing['user_code'],
                      pairing['verification_url'])
        self._poll(pairing['device_code'], interval, deadline)

    def _poll(self, device_code, interval, deadline):
        while True:
            # Sleep until the next poll or the deadline, whichever is sooner.
            self._sleep(max(0, min(interval, deadline - self._now())))
            if self._cancelled.is_set():
                return
            if self._now() >= deadline:
                self._deliver(self._on_error, EXPIRED, None)
                return
            result = self._client.desktop_poll(device_code)
            status = result.get('status')
            if status == 'pending':
                continue
            if status == 'approved' and result.get('key') \
                    and result.get('username'):
                self._deliver(self._approved, result['key'],
                              result['username'])
                return
            self._unexpected(status)
            return

    def _unexpected(self, status):
        # Fail loudly rather than keep polling a response this code was never
        # taught to read. Only the status goes in the message: the response
        # may carry a token, and this text is shown to the user.
        self._deliver(self._on_error, FAILED, AccountError(
            200, 'unexpected pairing response: status=%r' % (status,)))

    def _approved(self, key, username):
        # Runs on the UI thread under _deliver's guard, so a cancel() that
        # wins the race leaves the store untouched. clear() first, exactly as
        # AccountClient.login() does, or the previous account's last_upload
        # leaks into this one.
        self._store.clear()
        self._store.set(key, username)
        self._on_done(username)

    def _deliver(self, fn, *args):
        # The cancelled check must run when the callback executes, not when
        # it is queued: wx.CallAfter defers, so a callback queued just before
        # cancel() would otherwise still fire into a dialog that has moved on
        # or been destroyed.
        def _guarded():
            if not self._cancelled.is_set():
                fn(*args)
        self._dispatch(_guarded)

# Desktop Passkey Sign-in (PC Client) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let E-Tipitaka-PC users sign in with a passkey by handing the WebAuthn ceremony to their browser and collecting the resulting account token by polling, plus one-click links to passkey sign-up, passkey management and account recovery.

**Architecture:** A new UI-free `account/pairing.py` owns a worker thread that calls two new `AccountClient` methods (`desktop_begin`, `desktop_poll`) against the already-deployed server endpoints, and reports back through an injected `dispatch` (`wx.CallAfter` in the app, a plain call in tests). `AccountDialog` gains a third render state that shows the pairing code while the browser does the passkey sign-in. The token that comes back is the same DRF token password sign-in stores, so the sync code is untouched.

**Tech Stack:** Python 3.12, wxPython 4.2, `requests`, stdlib `threading` / `webbrowser`, `unittest` (run through `test.py`). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-18-desktop-passkey-design.md` (Client section). Server half is live at `https://data.etipitaka.com` and was verified end to end on 2026-09-18.

---

## Before you start

**Run every Python command through Homebrew's Python.** uv's standalone Python segfaults wxPython on macOS:

```bash
uv run --python /opt/homebrew/bin/python3.12 python <args>
```

Every command below is written out in full; do not shorten it to `python`.

**`test.py` always exits 0**, even when tests fail — it calls `runner.run()` and never `sys.exit()`. Judge it by its last lines (`Ran N tests` and `OK` / `FAILED (...)`), never by the exit code. Single modules run with `-m unittest` *do* exit non-zero, which is why the red/green steps below use that form.

**`-m unittest` ignores `suite()`.** It discovers every `test*` method, while `test.py` runs only the names each module lists in its `suite()` function. A method missing from `suite()` passes under `-m unittest` and never runs in `test.py`. Every task that adds tests runs this check:

```bash
uv run --python /opt/homebrew/bin/python3.12 python -c "
import unittest, tests.test_account_pairing as m
listed = m.suite().countTestCases()
found = unittest.defaultTestLoader.loadTestsFromModule(m).countTestCases()
print('suite() lists %d of %d test methods' % (listed, found))
assert listed == found, 'a test method is missing from suite()'"
```

(For the client module, substitute `tests.test_account_client`.)

**Branch.** The plan is committed on `feat/desktop-passkey`. Confirm you are on it (`git branch --show-current`). Never commit on `master`.

**Do not stage** `uv.lock` (it carries an unrelated local modification) or any `*.sqlite` file (project rule in `CLAUDE.md`). The working tree also holds untracked `.serena/`, `.venv-x86/`, `db_patch.toml` and `patches/` that predate this work. They are not yours: do not stage, move or delete them. Stage files by explicit path, never `git add -A`.

**Baseline:** `uv run --python /opt/homebrew/bin/python3.12 python test.py` → `Ran 97 tests` … `OK`.

---

## The server, as it actually behaves

Captured from production on 2026-09-18. Build against these, not against the spec's summary.

`POST /api/passkeys/desktop/begin/` with body `{}` → **200**:

```json
{"device_code": "<43 chars, the app's secret, never shown>",
 "user_code": "QS3E-MT4Z",
 "verification_url": "https://data.etipitaka.com/desktop/?code=QS3E-MT4Z",
 "interval": 5, "expires_in": 600}
```

`POST /api/passkeys/desktop/poll/` with body `{"device_code": "..."}`:

| Response | Meaning | Client does |
|---|---|---|
| 200 `{"status": "pending"}` | user has not decided | wait `interval`, poll again |
| 200 `{"status": "approved", "key": "<40-char token>", "username": "sutee"}` | approved; **the pairing is now consumed** | store token, done |
| 200 `{"status": "denied"}` | user pressed No; consumed | stop, say they refused |
| 400 `{"detail": "คำขอเข้าสู่ระบบนี้หมดอายุแล้ว กรุณาลองใหม่"}` | unknown, expired **or already used** — deliberately indistinguishable | stop, say it expired |
| 429 | rate limited; **pairing is still live** | back off by `Retry-After`, keep polling |

Things the spec does not say, each verified live:

- **The token is delivered at most once.** The server deletes the row in the same transaction that mints the token. If the approving response is lost in transit, the next poll is a 400. There is nothing to retry; the user starts over.
- **Two different 429 bodies.** nginx's edge limit returns `{"error":"rate_limited","retry_after":5,"detail":"..."}` with `Retry-After: 5`. DRF's own throttle returns only `{"detail":"Request was throttled. Expected available in N seconds."}` with `Retry-After: N` (up to ~60). **Only the `Retry-After` header is common to both**, so that is what the client reads.
- **Messages are Thai unless the `django_language` cookie says otherwise;** `Accept-Language` is ignored. This dialog is hardcoded Thai, so the default is right and the client sends no cookie.

## Deviations from the spec

Each is deliberate; Task 8 records them in the spec so it stays true.

1. **Labels say พาสคีย์, not "Passkey".** The browser confirmation page asks `คุณเพิ่งกด "เข้าสู่ระบบด้วยพาสคีย์" บนคอมพิวเตอร์ใช่ไหม?` — it quotes the desktop button *by name*. The button must read exactly `เข้าสู่ระบบด้วยพาสคีย์`, or the page tells the user to look for a button that isn't there. (The server had this exact bug; it was fixed in data-etipitaka `adbf87f`.)
2. **Closing the window cancels a pairing instead of being vetoed.** The spec copied the veto used for short requests; a pairing lasts up to ten minutes, and a close button that does nothing for that long reads as a hang. `cancel()` guarantees no callback reaches the dialog afterwards — which is the only thing the veto protects.
3. **The poll loop handles 429 and 400**, which the spec's loop rules omit (see the table above).
4. **The token is stored on the UI thread, only if the session was not cancelled.** A cancel that races an approval leaves the app signed out.
5. **`on_error` receives a reason code** (`DENIED` / `EXPIRED` / `FAILED`) rather than a message, so `pairing.py` holds no user-facing text and the tests assert on stable values.

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `account/client.py` | modify | `RateLimited(AccountError)` carrying `retry_after`; `desktop_begin()`, `desktop_poll()` |
| `account/pairing.py` | **create** | `PairingSession`: worker thread, poll loop, cancellation, token storage. No wx. |
| `account/dialogs.py` | modify | `AccountDialog`: passkey sign-in button, pairing render state, browser links |
| `constants.py` | modify | three browser URLs beside `ACCOUNT_BASE_URL` |
| `tests/test_account_client.py` | modify | 429 handling, the two desktop methods |
| `tests/test_account_pairing.py` | **create** | the whole `PairingSession` state machine, headless |
| `test.py` | modify | register the new test module |
| `PRIVACY.md` | modify | passkey paragraph |
| `docs/superpowers/specs/2026-09-18-desktop-passkey-design.md` | modify | amendments section |

`account/dialogs.py` has no automated tests anywhere in the repo, and no wx-level tests exist. Keeping every decision in `pairing.py` is what keeps that untested surface thin. The dialog is covered by a render smoke check (Tasks 6–7) and by manual verification against production (Task 10).

---

### Task 1: `RateLimited` carries the server's `Retry-After`

**Files:**
- Modify: `account/client.py` (after `AccountError` at line 13; after `_extract_message` at line 30; `_raise_if_error` at lines 145-147)
- Test: `tests/test_account_client.py`

A 429 has to be told apart from other errors, because for a pairing it means "slow down" rather than "failed". Raising a subclass keeps every existing `except AccountError` working.

- [ ] **Step 1: Let the response helper carry headers**

In `tests/test_account_client.py`, replace the `_resp` helper (lines 16-25) with:

```python
def _resp(status=200, json_body=None, content=b'', headers=None):
    r = MagicMock()
    r.status_code = status
    r.ok = 200 <= status < 300
    r.json = MagicMock(return_value=json_body if json_body is not None else {})
    if json_body is not None and not content:
        content = json.dumps(json_body).encode('utf-8')
    r.content = content
    r.text = json.dumps(json_body) if json_body is not None else content.decode('utf-8', 'ignore')
    # Case-insensitive like a real requests response, and a real mapping
    # rather than the MagicMock default: int() of a MagicMock is 1, so a
    # mocked response would otherwise appear to send "Retry-After: 1".
    r.headers = CaseInsensitiveDict(headers or {})
    return r
```

And change the import on line 9 to:

```python
from account.client import AccountClient, AccountError, RateLimited
```

and add a third-party import group below the `from unittest.mock import patch, MagicMock` line, separated from it by a blank line (PEP 8 grouping):

```python
from requests.structures import CaseInsensitiveDict
```

- [ ] **Step 2: Write the failing tests**

Add to `TestAccountClient`, after `testLoginClearsStaleLastUploadBeforeStoringNewToken`:

```python
    @patch('account.client.requests.post')
    def testRateLimitedCarriesRetryAfter(self, post):
        post.return_value = _resp(429, {'error': 'rate_limited', 'retry_after': 5,
                                        'detail': 'Too many requests.'},
                                  headers={'Retry-After': '5'})
        with self.assertRaises(RateLimited) as cm:
            self.client.login('alice', 'pw')
        self.assertIsInstance(cm.exception, AccountError)
        self.assertEqual(429, cm.exception.status)
        self.assertEqual(5, cm.exception.retry_after)
        self.assertEqual('Too many requests.', cm.exception.message)

    @patch('account.client.requests.post')
    def testRateLimitedReadsTheHeaderNotTheBody(self, post):
        # DRF's own throttle sends no retry_after key in the body at all --
        # only the header, which is the one thing both limiters agree on.
        post.return_value = _resp(
            429, {'detail': 'Request was throttled. Expected available in 42 seconds.'},
            headers={'Retry-After': '42'})
        with self.assertRaises(RateLimited) as cm:
            self.client.login('alice', 'pw')
        self.assertEqual(42, cm.exception.retry_after)

    @patch('account.client.requests.post')
    def testRateLimitedWithoutAHeaderHasNoRetryAfter(self, post):
        post.return_value = _resp(429, {'detail': 'slow down'})
        with self.assertRaises(RateLimited) as cm:
            self.client.login('alice', 'pw')
        self.assertIsNone(cm.exception.retry_after)

    @patch('account.client.requests.post')
    def testRateLimitedWithAnUnusableHeaderHasNoRetryAfter(self, post):
        # HTTP also allows an HTTP-date here, and a proxy could send a fraction
        # or a negative number. Not one of these may escape as a ValueError: in
        # the pairing loop that would end a pairing that is still live.
        for value in ('Wed, 21 Oct 2015 07:28:00 GMT', '1.5', '-3'):
            post.return_value = _resp(429, {'detail': 'slow down'},
                                      headers={'Retry-After': value})
            with self.assertRaises(RateLimited) as cm:
                self.client.login('alice', 'pw')
            self.assertIsNone(cm.exception.retry_after, value)

    @patch('account.client.requests.post')
    def testOtherErrorsAreNotRateLimited(self, post):
        # A 5xx in particular must stay a plain AccountError: the pairing loop
        # never counts a RateLimited as a failure, so a misclassified outage
        # would poll for the whole ten minutes instead of giving up.
        for status in (400, 500, 503):
            post.return_value = _resp(status, {'detail': 'nope'})
            with self.assertRaises(AccountError) as cm:
                self.client.login('alice', 'wrong')
            self.assertIs(AccountError, type(cm.exception), status)
```

Add the five names to the list in `suite()`, after `'testLoginClearsStaleLastUploadBeforeStoringNewToken'`. Keep `'testOtherErrorsAreNotRateLimited'` last: Task 2 extends the list from that line.

```python
                 'testLoginClearsStaleLastUploadBeforeStoringNewToken',
                 'testRateLimitedCarriesRetryAfter',
                 'testRateLimitedReadsTheHeaderNotTheBody',
                 'testRateLimitedWithoutAHeaderHasNoRetryAfter',
                 'testRateLimitedWithAnUnusableHeaderHasNoRetryAfter',
                 'testOtherErrorsAreNotRateLimited']:
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v
```

Expected: the module fails to import — `ImportError: cannot import name 'RateLimited' from 'account.client'`.

- [ ] **Step 4: Implement**

In `account/client.py`, directly after the `AccountError` class (after line 12):

```python
class RateLimited(AccountError):
    """A 429. `retry_after` is the server's Retry-After header in seconds, or
    None if it sent none that is a whole, non-negative number.

    Both of the server's rate limiters send that header, with different
    bodies: nginx's edge limit returns {"error", "retry_after", "detail"},
    while DRF's own throttle returns only {"detail"}. The header is the one
    thing they agree on, so it is what this reads.
    """

    def __init__(self, status, message, retry_after=None):
        super(RateLimited, self).__init__(status, message)
        self.retry_after = retry_after
```

Directly after `_extract_message` (after line 30):

```python
def _retry_after(resp):
    try:
        seconds = int(resp.headers.get('Retry-After'))
    except (TypeError, ValueError):
        return None
    # A negative delay is nonsense; report "unknown" rather than pass it on.
    # (An HTTP-date or a fraction already landed in ValueError above.)
    return seconds if seconds >= 0 else None
```

Replace `_raise_if_error` (the last method in the file) with:

```python
    def _raise_if_error(self, resp):
        if resp.status_code == 429:
            raise RateLimited(429, _extract_message(resp), _retry_after(resp))
        if not resp.ok:
            raise AccountError(resp.status_code, _extract_message(resp))
```

- [ ] **Step 5: Run to verify it passes**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v
```

Expected: `Ran 20 tests` … `OK`. Then run the `suite()` check from *Before you start* with `tests.test_account_client`: expected `suite() lists 20 of 20 test methods`.

- [ ] **Step 6: Prove the header test can fail**

Apply each mutation alone, run the module, see the named test **FAIL**, and restore before the next:

| Mutation in `account/client.py` | Test that must fail |
|---|---|
| `_retry_after` reads the body: `seconds = int(resp.json().get('retry_after'))` | `testRateLimitedReadsTheHeaderNotTheBody` |
| Narrow `except (TypeError, ValueError)` to `except TypeError` | `testRateLimitedWithAnUnusableHeaderHasNoRetryAfter` |
| `return seconds` instead of rejecting negatives | `testRateLimitedWithAnUnusableHeaderHasNoRetryAfter` (on `'-3'`) |
| `if resp.status_code >= 429:` | `testOtherErrorsAreNotRateLimited` |

And one that must **not** fail: changing `.get('Retry-After')` to `.get('retry-after')` keeps every test green, because the fixture is case-insensitive like a real `requests` response.

- [ ] **Step 7: Commit**

```bash
git add account/client.py tests/test_account_client.py
git commit -m "feat(account): RateLimited carries the server's Retry-After" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `desktop_begin` and `desktop_poll`

**Files:**
- Modify: `account/client.py` (a `_pairing_body` helper after `_retry_after`; new methods after `delete_backup`, before `_auth_headers`)
- Test: `tests/test_account_client.py`

Both follow the file's existing shape: bare `requests.post`, `_raise_if_error`, return the parsed body. Neither stores anything — `PairingSession` decides whether a token is kept (Task 3), which is what lets a cancel discard it.

The parsed body must be a JSON object. `_pairing_body` turns anything else (empty, a list, a bare string) into an `AccountError`, which `PairingSession` retries like any other failure, rather than an `AttributeError` that would end the session at once.

- [ ] **Step 1: Write the failing tests**

Add to `TestAccountClient`, after `testOtherErrorsAreNotRateLimited`:

```python
    @patch('account.client.requests.post')
    def testDesktopBeginPostsAnEmptyObject(self, post):
        body = {'device_code': 'dev-secret', 'user_code': 'ABCD-2345',
                'verification_url': BASE + '/desktop/?code=ABCD-2345',
                'interval': 5, 'expires_in': 600}
        post.return_value = _resp(200, body)
        self.assertEqual(body, self.client.desktop_begin())
        post.assert_called_once_with(
            BASE + '/api/passkeys/desktop/begin/', json={}, timeout=30)

    @patch('account.client.requests.post')
    def testDesktopBeginRejectsAnIncompleteResponse(self, post):
        good = {'device_code': 'dev-secret', 'user_code': 'ABCD-2345',
                'verification_url': BASE + '/desktop/?code=ABCD-2345'}
        for key in good:
            missing = {k: v for k, v in good.items() if k != key}
            for broken in (missing, dict(good, **{key: ''}),
                           dict(good, **{key: None})):
                post.return_value = _resp(200, broken)
                with self.assertRaises(AccountError, msg=repr(broken)) as cm:
                    self.client.desktop_begin()
                self.assertIn(key, cm.exception.message, repr(broken))

    @patch('account.client.requests.post')
    def testDesktopBeginRaisesTheServersError(self, post):
        post.return_value = _resp(429, {'error': 'rate_limited', 'retry_after': 5,
                                        'detail': 'Too many requests.'},
                                  headers={'Retry-After': '5'})
        with self.assertRaises(RateLimited) as cm:
            self.client.desktop_begin()
        self.assertEqual('Too many requests.', cm.exception.message)
        post.return_value = _resp(503, {'detail': u'ระบบปิดปรับปรุง'})
        with self.assertRaises(AccountError) as cm:
            self.client.desktop_begin()
        self.assertEqual(503, cm.exception.status)
        self.assertEqual(u'ระบบปิดปรับปรุง', cm.exception.message)

    @patch('account.client.requests.post')
    def testDesktopRejectsABodyThatIsNotAnObject(self, post):
        calls = {'begin': self.client.desktop_begin,
                 'poll': lambda: self.client.desktop_poll('dev-secret')}
        for name, call in calls.items():
            for resp in (_resp(200), _resp(200, []), _resp(200, 'ok'),
                         _resp(200, 5)):
                post.return_value = resp
                with self.assertRaises(AccountError, msg=name) as cm:
                    call()
                self.assertEqual(200, cm.exception.status, name)
                self.assertEqual('unexpected pairing response',
                                 cm.exception.message, name)

    @patch('account.client.requests.post')
    def testDesktopPollPostsTheDeviceCodeAndStoresNothing(self, post):
        self.store.set('old-tok', 'bob')
        approved = {'status': 'approved', 'key': 'tok', 'username': 'alice'}
        post.return_value = _resp(200, approved)
        self.assertEqual(approved, self.client.desktop_poll('dev-secret'))
        post.assert_called_once_with(
            BASE + '/api/passkeys/desktop/poll/',
            json={'device_code': 'dev-secret'}, timeout=30)
        # Neither replaced nor wiped: the token already here is untouched.
        self.assertEqual('old-tok', self.store.get()['token'])
        self.assertEqual('bob', self.store.get()['username'])

    @patch('account.client.requests.post')
    def testDesktopPollRaises400WhenThePairingIsGone(self, post):
        post.return_value = _resp(
            400, {'detail': u'คำขอเข้าสู่ระบบนี้หมดอายุแล้ว กรุณาลองใหม่'})
        with self.assertRaises(AccountError) as cm:
            self.client.desktop_poll('dev-secret')
        self.assertEqual(400, cm.exception.status)

    @patch('account.client.requests.post')
    def testDesktopPollRaisesRateLimited(self, post):
        post.return_value = _resp(429, {'error': 'rate_limited', 'retry_after': 5,
                                        'detail': 'Too many requests.'},
                                  headers={'Retry-After': '5'})
        with self.assertRaises(RateLimited) as cm:
            self.client.desktop_poll('dev-secret')
        self.assertEqual(5, cm.exception.retry_after)
```

Extend the `suite()` list after `'testOtherErrorsAreNotRateLimited'`:

```python
                 'testOtherErrorsAreNotRateLimited',
                 'testDesktopBeginPostsAnEmptyObject',
                 'testDesktopBeginRejectsAnIncompleteResponse',
                 'testDesktopBeginRaisesTheServersError',
                 'testDesktopRejectsABodyThatIsNotAnObject',
                 'testDesktopPollPostsTheDeviceCodeAndStoresNothing',
                 'testDesktopPollRaises400WhenThePairingIsGone',
                 'testDesktopPollRaisesRateLimited']:
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v
```

Expected: seven errors, `AttributeError: 'AccountClient' object has no attribute 'desktop_begin'` (and `'desktop_poll'`).

- [ ] **Step 3: Implement**

In `account/client.py`, after `_retry_after` and before `class AccountClient`:

```python
def _pairing_body(resp):
    # A pairing endpoint's 2xx body must be a JSON object. Anything else --
    # empty, a list, a bare string -- becomes an AccountError, one of the
    # errors PairingSession handles, instead of an AttributeError further
    # on. A body that is not JSON at all (a captive portal's HTML page, say)
    # still raises requests' JSONDecodeError, a RequestException, so it
    # counts as a network failure.
    body = resp.json() if resp.content else None
    if not isinstance(body, dict):
        raise AccountError(resp.status_code, 'unexpected pairing response')
    return body
```

Then, after `delete_backup` and before `_auth_headers`:

```python
    def desktop_begin(self):
        """Start a desktop passkey pairing (see account/pairing.py).

        Returns the server's dict: device_code (the app's secret -- never
        shown), user_code (shown to the user), verification_url (opened in
        the browser), interval and expires_in (seconds).
        """
        resp = requests.post(
            self._base + '/api/passkeys/desktop/begin/',
            json={},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        body = _pairing_body(resp)
        for key in ('device_code', 'user_code', 'verification_url'):
            if not body.get(key):
                raise AccountError(resp.status_code,
                                   'pairing response missing %s' % key)
        return body

    def desktop_poll(self, device_code):
        """Poll a pairing once. Returns the server's dict:
        {'status': 'pending'}, {'status': 'denied'}, or
        {'status': 'approved', 'key': ..., 'username': ...}.

        Raises AccountError(400) once the pairing is unknown, expired or
        already used -- the server deliberately does not say which --
        RateLimited on a 429, and AccountError if a 2xx body is not a JSON
        object. Stores nothing: PairingSession decides whether a token is
        kept.
        """
        resp = requests.post(
            self._base + '/api/passkeys/desktop/poll/',
            json={'device_code': device_code},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return _pairing_body(resp)
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v
```

Expected: `Ran 27 tests` … `OK`. `suite()` check with `tests.test_account_client`: `suite() lists 27 of 27 test methods`.

- [ ] **Step 5: Prove the validation tests can fail**

One at a time, re-running after each and restoring before the next:
- Delete the `for key in (...)` check in `desktop_begin`. Expected: `testDesktopBeginRejectsAnIncompleteResponse` **FAILS** (`AccountError not raised`).
- In `desktop_poll`, return `resp.json()` instead of `_pairing_body(resp)`. Expected: `testDesktopRejectsABodyThatIsNotAnObject` **FAILS** (`AccountError not raised : poll`).

Restore and confirm green.

- [ ] **Step 6: Commit**

```bash
git add account/client.py tests/test_account_client.py
git commit -m "feat(account): client calls for desktop passkey pairing" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `PairingSession` — happy path and cancellation

**Files:**
- Create: `account/pairing.py`
- Create: `tests/test_account_pairing.py`
- Modify: `test.py`

This task builds the session's skeleton: begin, report the code, poll until approved or expired, store the token, and cancel cleanly. Tasks 4 and 5 widen `_poll` to handle every other server response.

Three properties matter more than the rest, and each has a test built to catch its violation:

- **"No callback after `cancel()`" is enforced when the callback *executes*, not when it is queued.** `wx.CallAfter` defers. A callback the worker queued a moment before the user pressed Cancel would otherwise still run, into a dialog that has moved on or been destroyed.
- **The token is written under that same guard**, so cancelling means nothing happened locally.
- **Every session ends in a callback, even when writing the token fails.** `_approved` runs on the UI thread, where `run()`'s catch-all cannot see it, so it catches its own store errors. Otherwise a full disk would leave the dialog waiting forever for a token the server has already handed out.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_account_pairing.py`:

```python
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
```

`requests`, `AccountError`, `RateLimited` and `DENIED` are imported now but first used in Tasks 4-5. Leave them.

- [ ] **Step 2: Register the module in `test.py`**

Three edits, matching the existing pattern:

After `import tests.test_compare_close` add:
```python
import tests.test_account_pairing
```
After `suite9 = tests.test_compare_close.suite()` add:
```python
suite10 = tests.test_account_pairing.suite()
```
Replace the `alltests` line with:
```python
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5, suite6, suite7, suite8, suite9, suite10])
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: `ModuleNotFoundError: No module named 'account.pairing'`.

- [ ] **Step 4: Implement**

Create `account/pairing.py`:

```python
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
        try:
            self._store.clear()
            self._store.set(key, username)
        except Exception as e:
            # A full disk or a read-only config dir. This runs on the UI
            # thread, where run()'s catch-all cannot see it, so end the
            # session here or the dialog waits forever. The server has
            # already handed out the token; the user must start over.
            self._on_error(FAILED, AccountError(-1, str(e)))
            return
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
```

- [ ] **Step 5: Run to verify it passes**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: `Ran 13 tests` … `OK`. Then the `suite()` check from *Before you start*: `suite() lists 13 of 13 test methods`.

- [ ] **Step 6: Prove the six guarantees can fail**

Apply each mutation alone, run the module, see the named test **FAIL**, and restore before the next:

| Mutation in `account/pairing.py` | Test that must fail |
|---|---|
| In `_deliver`, replace `_guarded` with a direct `self._dispatch(lambda: fn(*args))` | `testCancelDropsACallbackAlreadyQueued` |
| In `__init__`, make the default `time.sleep` instead of `self._cancelled.wait` | `testCancelWakesTheDefaultSleepPromptly` (after ~2s) |
| In `_approved`, delete `self._store.clear()` | `testApprovalReplacesThePreviousAccount` |
| In `_poll`, change `self._unexpected(status)` to `self._unexpected(result)`, so the whole response — token included — lands in the message | `testApprovedWithoutUsernameFailsWithoutLeakingTheToken` |
| In `_approved`, remove the `try`/`except`, leaving the two store calls unguarded | `testAFailedTokenWriteStillEndsTheSession` (`OSError` escapes the drained queue) |
| In `_approved`, move `self._on_done(username)` above the store calls | `testTheTokenIsStoredBeforeOnDoneRuns` |

After restoring, re-run and confirm `OK`.

- [ ] **Step 7: Commit**

```bash
git add account/pairing.py tests/test_account_pairing.py test.py
git commit -m "feat(account): PairingSession for desktop passkey sign-in" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `PairingSession` — refusal and a vanished pairing

**Files:**
- Modify: `account/pairing.py` (`_poll`)
- Test: `tests/test_account_pairing.py`

Two server answers end a session without a token and need their own reasons: `denied` (the user pressed No) and HTTP 400 (the pairing is unknown, expired or already used). A client has to tell these apart — "you said no" versus "start over".

- [ ] **Step 1: Write the failing tests**

Add to `TestPairingSession`, after `testApprovedWithoutUsernameFailsWithoutLeakingTheToken`:

```python
    # --- the server ends it ----------------------------------------------

    def testDenialEndsTheSession(self):
        client = FakeClient(_begin(), [PENDING, REFUSED])
        self._session(client).run()
        self.assertEqual(('error', DENIED, None), self.rec.events[-1])
        self.assertEqual(2, len(client.poll_calls))
        self.assertFalse(self.store.is_logged_in())

    def testA400EndsTheSessionAsExpired(self):
        # Also what happens when an approval's response is lost in transit:
        # the server hands the token over at most once, so the retry is a 400.
        client = FakeClient(_begin(), [PENDING, AccountError(400, 'gone')])
        self._session(client).run()
        self.assertEqual(('error', EXPIRED, None), self.rec.events[-1])
        self.assertEqual(2, len(client.poll_calls))
```

Add both names to `suite()`, after `'testApprovedWithoutUsernameFailsWithoutLeakingTheToken'`:

```python
                 'testApprovedWithoutUsernameFailsWithoutLeakingTheToken',
                 'testDenialEndsTheSession',
                 'testA400EndsTheSessionAsExpired',
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: both new tests FAIL. Denial reports `FAILED` (unrecognised status) instead of `DENIED`; the 400 escapes to `run()`'s catch-all and reports `FAILED` instead of `EXPIRED`.

- [ ] **Step 3: Implement**

Replace `_poll` in `account/pairing.py` with:

```python
    def _poll(self, device_code, interval, deadline):
        while True:
            # Sleep until the next poll or the deadline, whichever is sooner.
            self._sleep(max(0, min(interval, deadline - self._now())))
            if self._cancelled.is_set():
                return
            if self._now() >= deadline:
                self._deliver(self._on_error, EXPIRED, None)
                return
            try:
                result = self._client.desktop_poll(device_code)
            except AccountError as e:
                if e.status != 400:
                    raise
                # Unknown, expired or already used -- the server will not
                # say which. "Already used" includes an approval whose
                # response never reached us: the token is delivered at most
                # once, so there is nothing left to retry.
                self._deliver(self._on_error, EXPIRED, None)
                return
            status = result.get('status')
            if status == 'pending':
                continue
            if status == 'denied':
                self._deliver(self._on_error, DENIED, None)
                return
            if status == 'approved' and result.get('key') \
                    and result.get('username'):
                self._deliver(self._approved, result['key'],
                              result['username'])
                return
            self._unexpected(status)
            return
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: `Ran 15 tests` … `OK`. `suite()` check: `suite() lists 15 of 15 test methods`.

- [ ] **Step 5: Prove the denial test can fail**

In the `denied` branch, temporarily report `EXPIRED` instead of `DENIED`. Expected: `testDenialEndsTheSession` **FAILS**. Restore; confirm green.

- [ ] **Step 6: Commit**

```bash
git add account/pairing.py tests/test_account_pairing.py
git commit -m "feat(account): end a pairing on refusal or when the server drops it" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `PairingSession` — network failures and rate limits

**Files:**
- Modify: `account/pairing.py` (imports, constants, `_handshake`, `_poll`)
- Test: `tests/test_account_pairing.py`

The browser leg is slow: the user may take minutes to sign in. A single dropped request must not end a live pairing, so transient failures are retried with a doubling wait and only three *consecutive* ones end the session. A 429 is not a failure at all — the pairing is still live, so the session backs off by `Retry-After` and continues.

- [ ] **Step 1: Write the failing tests**

Add to `TestPairingSession`, after `testA400EndsTheSessionAsExpired`:

```python
    # --- resilience --------------------------------------------------------

    def testBeginNetworkFailureReportsFailed(self):
        client = FakeClient(requests.ConnectionError('offline'), [])
        self._session(client).run()
        self.assertEqual(1, len(self.rec.events))
        # Status 0 is what the dialog words as "cannot reach the server".
        self.assertEqual(0, self._failed().status)
        self.assertEqual([], client.poll_calls)

    def testBeginServerErrorIsPassedThrough(self):
        boom = AccountError(503, 'maintenance')
        client = FakeClient(boom, [])
        self._session(client).run()
        self.assertEqual([('error', FAILED, boom)], self.rec.events)

    def testATransientFailureIsRetriedWithBackoff(self):
        client = FakeClient(_begin(), [PENDING, requests.ConnectionError('blip'),
                                       APPROVED])
        self._session(client).run()
        self.assertEqual(('done', 'alice'), self.rec.events[-1])
        self.assertEqual([5, 5, 10], self.clock.sleeps)

    def testThreeConsecutiveFailuresEndTheSession(self):
        client = FakeClient(_begin(), [requests.ConnectionError('down')] * 3)
        self._session(client).run()
        self.assertEqual(0, self._failed().status)
        self.assertEqual(3, len(client.poll_calls))
        self.assertEqual([5, 10, 20], self.clock.sleeps)

    def testServerErrorsCountAsFailuresToo(self):
        # Only a 400 means the pairing is gone. Anything else -- a 503 during
        # maintenance, a 200 whose body was not a JSON object -- is retried.
        client = FakeClient(_begin(), [AccountError(s, 'x')
                                       for s in (200, 404, 503)])
        self._session(client).run()
        self.assertEqual(503, self._failed().status)
        self.assertEqual(3, len(client.poll_calls))

    def testTheFailureCountResetsOnAnyGoodResponse(self):
        blip = requests.ConnectionError('blip')
        client = FakeClient(_begin(), [blip, blip, PENDING, blip, blip, APPROVED])
        self._session(client).run()
        self.assertEqual(('done', 'alice'), self.rec.events[-1])
        self.assertEqual(6, len(client.poll_calls))
        # The wait resets too: back to the interval, then doubling afresh.
        self.assertEqual([5, 10, 20, 5, 10, 20], self.clock.sleeps)

    def testARateLimitIsNotAFailure(self):
        # Four 429s in a row, more than MAX_FAILURES, and the session lives.
        limited = RateLimited(429, 'slow down', retry_after=30)
        client = FakeClient(_begin(), [limited] * 4 + [APPROVED])
        self._session(client).run()
        self.assertEqual(('done', 'alice'), self.rec.events[-1])
        self.assertEqual([5, 30, 30, 30, 30], self.clock.sleeps)

    def testARateLimitNeverPollsFasterThanTheInterval(self):
        client = FakeClient(_begin(), [RateLimited(429, '', retry_after=1),
                                       APPROVED])
        self._session(client).run()
        self.assertEqual([5, 5], self.clock.sleeps)

    def testARateLimitWaitIsCapped(self):
        client = FakeClient(_begin(), [RateLimited(429, '', retry_after=3600),
                                       APPROVED])
        self._session(client).run()
        self.assertEqual([5, 60], self.clock.sleeps)

    def testARateLimitWithoutRetryAfterWaitsTheInterval(self):
        client = FakeClient(_begin(), [RateLimited(429, ''), APPROVED])
        self._session(client).run()
        self.assertEqual([5, 5], self.clock.sleeps)
```

Add all ten names to `suite()`, after `'testA400EndsTheSessionAsExpired'`:

```python
                 'testA400EndsTheSessionAsExpired',
                 'testBeginNetworkFailureReportsFailed',
                 'testBeginServerErrorIsPassedThrough',
                 'testATransientFailureIsRetriedWithBackoff',
                 'testThreeConsecutiveFailuresEndTheSession',
                 'testServerErrorsCountAsFailuresToo',
                 'testTheFailureCountResetsOnAnyGoodResponse',
                 'testARateLimitIsNotAFailure',
                 'testARateLimitNeverPollsFasterThanTheInterval',
                 'testARateLimitWaitIsCapped',
                 'testARateLimitWithoutRetryAfterWaitsTheInterval',
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: all ten new tests FAIL. Each exception currently escapes to `run()`'s catch-all, which reports `FAILED` with status `-1` after a single poll.

- [ ] **Step 3: Implement**

In `account/pairing.py`, replace the imports with:

```python
import threading
import time

import requests

from account.client import AccountError, RateLimited
```

Replace the constants block with:

```python
DEFAULT_INTERVAL = 5      # seconds; used when the server's value is unusable
DEFAULT_EXPIRES_IN = 600
MAX_FAILURES = 3          # consecutive transient failures before giving up
MAX_WAIT = 60             # cap on any single wait, Retry-After included
```

Directly after `_seconds`, add:

```python
def _network_error(e):
    # Status 0 is what dialogs._show_error words as "cannot reach the
    # server" -- the same convention as _run_in_thread there.
    return AccountError(0, str(e))
```

Replace `_handshake` with:

```python
    def _handshake(self):
        try:
            pairing = self._client.desktop_begin()
        except AccountError as e:
            self._deliver(self._on_error, FAILED, e)
            return
        except requests.RequestException as e:
            self._deliver(self._on_error, FAILED, _network_error(e))
            return
        interval = _seconds(pairing.get('interval'), DEFAULT_INTERVAL)
        deadline = self._now() + _seconds(pairing.get('expires_in'),
                                          DEFAULT_EXPIRES_IN)
        self._deliver(self._on_code, pairing['user_code'],
                      pairing['verification_url'])
        self._poll(pairing['device_code'], interval, deadline)
```

Replace `_poll` with:

```python
    def _poll(self, device_code, interval, deadline):
        wait = interval
        failures, last = 0, None
        while True:
            # Sleep until the next poll or the deadline, whichever is sooner.
            self._sleep(max(0, min(wait, deadline - self._now())))
            if self._cancelled.is_set():
                return
            if self._now() >= deadline:
                self._deliver(self._on_error, EXPIRED, None)
                return
            try:
                result = self._client.desktop_poll(device_code)
            except RateLimited as e:
                # Not a failure: the pairing is still live. Back off by what
                # the server asked, but never poll faster than the interval
                # and never sleep longer than MAX_WAIT.
                wait = min(max(interval, e.retry_after or 0), MAX_WAIT)
                continue
            except AccountError as e:
                if e.status == 400:
                    # Unknown, expired or already used -- the server will not
                    # say which. "Already used" includes an approval whose
                    # response never reached us: the token is delivered at
                    # most once, so there is nothing left to retry.
                    self._deliver(self._on_error, EXPIRED, None)
                    return
                failures, last = failures + 1, e
            except requests.RequestException as e:
                failures, last = failures + 1, _network_error(e)
            else:
                status = result.get('status')
                if status == 'pending':
                    wait, failures = interval, 0
                    continue
                if status == 'denied':
                    self._deliver(self._on_error, DENIED, None)
                    return
                if status == 'approved' and result.get('key') \
                        and result.get('username'):
                    self._deliver(self._approved, result['key'],
                                  result['username'])
                    return
                self._unexpected(status)
                return
            if failures >= MAX_FAILURES:
                self._deliver(self._on_error, FAILED, last)
                return
            # The browser leg is slow, so one dropped request must not end a
            # live pairing: retry, doubling the wait each time.
            wait = min(interval * 2 ** failures, MAX_WAIT)
```

`except RateLimited` has to come before `except AccountError`: `RateLimited` is a subclass and would otherwise be counted as a failure.

- [ ] **Step 4: Run to verify it passes**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_pairing -v
```

Expected: `Ran 25 tests` … `OK`. `suite()` check: `suite() lists 25 of 25 test methods`.

- [ ] **Step 5: Prove the resilience rules can fail**

| Mutation in `_poll` | Test that must fail |
|---|---|
| Delete the `except RateLimited` block, so a 429 falls into the `AccountError` branch | `testARateLimitIsNotAFailure` |
| In the `pending` branch, change `wait, failures = interval, 0` to `wait = interval` | `testTheFailureCountResetsOnAnyGoodResponse` |
| In the `pending` branch, change `wait, failures = interval, 0` to `failures = 0` | `testTheFailureCountResetsOnAnyGoodResponse` |
| Change `max(interval, e.retry_after or 0)` to `e.retry_after or interval` | `testARateLimitNeverPollsFasterThanTheInterval` |
| Change `if e.status == 400:` to `if e.status >= 400:`, so any client or server error ends the pairing | `testServerErrorsCountAsFailuresToo` |

Restore after each; confirm `OK`.

- [ ] **Step 6: Commit**

```bash
git add account/pairing.py tests/test_account_pairing.py
git commit -m "feat(account): ride out network blips and rate limits while pairing" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Dialog — passkey sign-in and the pairing screen

**Files:**
- Modify: `account/dialogs.py` (imports; `AccountDialog.__init__`, `_on_close`, `_render`, `_render_logged_out`; new methods)

No automated tests exist for this file, and none are added. This task has a render smoke check (Step 7) and is verified by hand against production in Task 10.

- [ ] **Step 1: Imports**

In `account/dialogs.py`, replace:

```python
import threading
import zipfile
from datetime import datetime
```

with:

```python
import threading
import webbrowser
import zipfile
from datetime import datetime
```

and replace:

```python
from account.client import AccountError
```

with:

```python
from account.client import AccountError
from account.pairing import PairingSession, DENIED, EXPIRED
```

- [ ] **Step 2: State and the pulse timer in `__init__`**

Replace:

```python
        super(AccountDialog, self).__init__(parent, title=u'บัญชีผู้ใช้',
                                            size=(380, 280))
        self._client = client
        self._store = tokenstore
        self._presenter = presenter
```

with:

```python
        super(AccountDialog, self).__init__(parent, title=u'บัญชีผู้ใช้',
                                            size=(420, 380))
        self._client = client
        self._store = tokenstore
        self._presenter = presenter

        self._pairing = None        # the PairingSession in flight, if any
        self._pairing_url = None
        # A single Gauge.Pulse() animates continuously on macOS and Windows
        # but moves one step on GTK, and a pairing can last ten minutes.
        self._pulse = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_pulse, self._pulse)
```

The timer must exist before `self._render()` runs at the end of `__init__`, because `_reset` (next step) stops it.

- [ ] **Step 3: Closing cancels; split `_render`**

Replace:

```python
    def _on_close(self, evt):
        # Veto window-manager close while a worker thread is in-flight.
        if any(not b.IsEnabled() for b in self._actionButtons):
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _render(self):
        self._sizer.Clear(delete_windows=True)
        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []
        if self._store.is_logged_in():
            self._render_logged_in()
        else:
            self._render_logged_out()
        self._panel.Layout()
        self.Layout()
```

with:

```python
    def _on_close(self, evt):
        if self._pairing is not None:
            # A pairing can run for ten minutes, so closing the window
            # cancels it instead of being vetoed. cancel() guarantees nothing
            # fires into this dialog afterwards -- the danger the veto below
            # exists to prevent for the short requests, which cannot be
            # cancelled.
            self._cancel_pairing()
        elif any(not b.IsEnabled() for b in self._actionButtons):
            # Veto window-manager close while a worker thread is in-flight.
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _reset(self):
        self._pulse.Stop()
        self._sizer.Clear(delete_windows=True)
        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []

    def _relayout(self):
        self._panel.Layout()
        self.Layout()

    def _render(self):
        self._reset()
        if self._store.is_logged_in():
            self._render_logged_in()
        else:
            self._render_logged_out()
        self._relayout()
```

- [ ] **Step 4: The passkey button on the signed-out screen**

Replace the whole `_render_logged_out` method (currently lines 391-421, from `def _render_logged_out(self):` down to the line before `def _render_logged_in(self):`) with:

```python
    def _render_logged_out(self):
        status = wx.StaticText(self._panel, label=u'เข้าสู่ระบบ: -')

        # The primary action. The label must stay exactly this: the
        # confirmation page in the browser asks whether the user just pressed
        # "เข้าสู่ระบบด้วยพาสคีย์" on their computer, quoting it by name.
        btnPasskey = wx.Button(self._panel, label=u'เข้าสู่ระบบด้วยพาสคีย์')
        btnPasskey.Bind(wx.EVT_BUTTON, self._on_passkey_login)

        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)
        self._username = wx.TextCtrl(self._panel)
        self._password = wx.TextCtrl(self._panel, style=wx.TE_PASSWORD)
        grid.Add(wx.StaticText(self._panel, label=u'ชื่อผู้ใช้'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._username, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self._panel, label=u'รหัสผ่าน'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._password, 1, wx.EXPAND)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnLogin = wx.Button(self._panel, label=u'เข้าสู่ระบบ')
        btnSignup = wx.Button(self._panel, label=u'สมัครสมาชิก...')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label=u'ปิด')
        btnLogin.Bind(wx.EVT_BUTTON, self._on_login)
        btnSignup.Bind(wx.EVT_BUTTON, self._on_signup)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        btnRow.Add(btnLogin, 0, wx.RIGHT, 6)
        btnRow.Add(btnSignup, 0)
        btnRow.AddStretchSpacer()
        btnRow.Add(btnClose, 0)

        self._actionButtons = [btnPasskey, btnLogin, btnSignup, btnClose]

        self._sizer.Add(status, 0, wx.ALL, 10)
        self._sizer.Add(btnPasskey, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(wx.StaticText(self._panel,
                        label=u'หรือใช้ชื่อผู้ใช้และรหัสผ่าน'),
                        0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
```

The password form and its behaviour are unchanged. Password sign-in stays: every existing user has a password, and it is the fallback.

- [ ] **Step 5: The pairing flow**

Insert after `AccountDialog._on_signup`. Anchor on this block, which is unique in the file:

```python
    def _on_signup(self, _evt):
        dlg = SignUpDialog(self, self._client)
        dlg.ShowModal()
        dlg.Destroy()
```

Add directly after it:

```python
    # --- passkey sign-in ---------------------------------------------------

    def _on_passkey_login(self, _evt):
        self._busy(True)
        self._pairing = PairingSession(
            self._client, self._store,
            on_code=self._show_pairing,
            on_done=self._on_pairing_done,
            on_error=self._on_pairing_error,
            dispatch=wx.CallAfter)
        self._pairing.start()

    def _show_pairing(self, user_code, url):
        self._pairing_url = url
        self._reset()
        self._render_pairing(user_code)
        self._relayout()
        self._pulse.Start(100)
        # The app opens the page itself, so the honest flow never involves
        # following a pairing link from anywhere else -- with the code in the
        # URL, a link from elsewhere is exactly what a phisher would send.
        # Rendered first, so the code is on screen before the browser takes
        # focus.
        self._open_browser(url)

    def _render_pairing(self, user_code):
        col = wx.BoxSizer(wx.VERTICAL)
        # Name the app beside the code: the browser page cannot say which
        # computer is asking, so this screen is the only place that can.
        col.Add(wx.StaticText(self._panel,
                label=u'E-Tipitaka บนคอมพิวเตอร์เครื่องนี้แสดงรหัส:'),
                0, wx.BOTTOM, 6)
        code = wx.StaticText(self._panel, label=user_code)
        code.SetFont(wx.Font(24, wx.FONTFAMILY_TELETYPE,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        col.Add(code, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 8)
        # A no-break space keeps the quoted button name on one line.
        hint = wx.StaticText(self._panel, label=(
            u'ลงชื่อเข้าใช้ในเบราว์เซอร์ที่เปิดขึ้น แล้วตรวจว่าหน้าเว็บแสดงรหัส'
            u'เดียวกันนี้ ถ้าไม่ตรงกัน อย่ากด "ใช่\u00a0อนุญาต"'))
        hint.Wrap(380)
        col.Add(hint, 0, wx.BOTTOM, 10)
        self._gauge.Show()
        col.Add(self._gauge, 0, wx.EXPAND | wx.BOTTOM, 4)
        col.Add(wx.StaticText(self._panel,
                label=u'กำลังรอการยืนยันในเบราว์เซอร์...'), 0)

        btnReopen = wx.Button(self._panel, label=u'เปิดเบราว์เซอร์อีกครั้ง')
        # wx.ID_CANCEL, so Esc cancels too. The handler below does not Skip(),
        # so the dialog's default Esc handling never ends the modal.
        btnCancel = wx.Button(self._panel, wx.ID_CANCEL, label=u'ยกเลิก')
        btnReopen.Bind(wx.EVT_BUTTON,
                       lambda _e: self._open_browser(self._pairing_url))
        btnCancel.Bind(wx.EVT_BUTTON, self._on_cancel_pairing)
        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnRow.Add(btnReopen, 0)
        btnRow.AddStretchSpacer()
        btnRow.Add(btnCancel, 0)

        self._actionButtons = [btnReopen, btnCancel]

        self._sizer.Add(col, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)

    def _on_pulse(self, _evt):
        self._gauge.Pulse()

    def _on_cancel_pairing(self, _evt):
        self._cancel_pairing()
        self._render()

    def _cancel_pairing(self):
        if self._pairing is not None:
            self._pairing.cancel()
            self._pairing = None
        self._pulse.Stop()

    def _on_pairing_done(self, _username):
        self._pairing = None
        self._render()          # the store now holds the token
        # The user is still in the browser: bounce the Dock icon / flash the
        # taskbar so they know to come back.
        self.RequestUserAttention()

    def _on_pairing_error(self, reason, err):
        self._pairing = None
        self._render()
        if reason == DENIED:
            wx.MessageBox(u'คำขอเข้าสู่ระบบถูกปฏิเสธในเบราว์เซอร์',
                          MSGBOX_TITLE, wx.OK | wx.ICON_INFORMATION, self)
        elif reason == EXPIRED:
            wx.MessageBox(u'คำขอเข้าสู่ระบบหมดอายุแล้ว กรุณาลองใหม่',
                          MSGBOX_TITLE, wx.OK | wx.ICON_WARNING, self)
        elif err.status == 0:
            _show_error(self, err)      # "cannot reach the server"
        else:
            # Not _show_error for the rest: its 401 and 404 wording is about
            # an existing session and backups. Say what failed, then why --
            # the server's Thai, or a local error such as a full disk. A 5xx
            # body is usually a proxy's HTML page, so name the status instead.
            detail = err.message
            if err.status >= 500 or not detail:
                detail = u'HTTP %d' % err.status
            wx.MessageBox(u'เข้าสู่ระบบด้วยพาสคีย์ไม่สำเร็จ\n\n%s' % detail,
                          MSGBOX_TITLE, wx.OK | wx.ICON_ERROR, self)

    def _open_browser(self, url):
        if not webbrowser.open_new(url):
            wx.MessageBox(
                u'เปิดเบราว์เซอร์ไม่ได้ กรุณาคัดลอกลิงก์นี้ไปเปิดเอง:\n\n%s' % url,
                MSGBOX_TITLE, wx.OK | wx.ICON_WARNING, self)
```

Notes for the reviewer:
- The pairing screen does not use `_busy()`. That would disable its own Cancel button. It shows the gauge and drives it with the timer instead.
- `_on_pairing_error` re-renders *before* showing the message box, so the signed-out screen is already behind the box.
- The dialog's `_on_err` is not used here. It clears the store on a 401, and no pairing response can be a 401.
- Only network failures (status 0) go through `_show_error`. Its 401 and 404 messages are about sessions and backups, so a 404 on begin would otherwise tell the user "backup not found".
- The pairing screen's Cancel button has `wx.ID_CANCEL`, so Esc cancels a pairing as well. Its handler does not call `Skip()`, which keeps the dialog's default Esc behaviour (ending the modal) from running.

- [ ] **Step 5b: `_busy` lays out the panel**

`AccountDialog._busy` lays out only the dialog. The gauge lives on the panel, so while begin is in flight it shows as a sliver at the panel's origin, on top of the status line. This predates this plan, but the passkey button is the first busy state a user sees on the signed-out screen. In `AccountDialog`, replace (the `for b in self._actionButtons:` line makes this block unique; the two other dialogs' `_busy` differ):

```python
    def _busy(self, on):
        for b in self._actionButtons:
            b.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()
```

with:

```python
    def _busy(self, on):
        for b in self._actionButtons:
            b.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        # The gauge lives on the panel: laying out only the dialog leaves it
        # a sliver at the panel's origin, over the status line.
        self._relayout()
```

- [ ] **Step 6: Import check**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -c "import account.dialogs; print('ok')"
```

Expected: `ok`.

- [ ] **Step 7: Render smoke check**

This builds the dialog in each state without showing it. It catches the failures most likely here: a wxPython sizer-flag assertion, a misspelled method, or a NameError on a render path. It patches `webbrowser.open_new` so no real browser opens. Do not commit it.

```bash
uv run --python /opt/homebrew/bin/python3.12 python - <<'PY'
import os, tempfile
import wx
import account.dialogs as d
from account.client import AccountClient
from account.tokenstore import TokenStore

d.webbrowser.open_new = lambda url: True        # never launch a real browser
app = wx.App(False)
store = TokenStore(os.path.join(tempfile.mkdtemp(), 'account.cfg'))
dlg = d.AccountDialog(None, AccountClient('https://example.invalid', store),
                      store, None)
print('signed out: ok')
dlg._show_pairing('ABCD-2345', 'https://example.invalid/desktop/?code=ABCD-2345')
assert dlg._pulse.IsRunning(), 'pulse timer not started'
print('pairing: ok')
dlg._cancel_pairing()
dlg._render()
assert not dlg._pulse.IsRunning(), 'pulse timer still running after cancel'
store.set('tok', 'alice')
dlg._render()
print('signed in: ok')
dlg.Destroy()
PY
```

Expected: `signed out: ok`, `pairing: ok`, `signed in: ok`, and no traceback.

- [ ] **Step 8: Full suite still green**

```bash
uv run --python /opt/homebrew/bin/python3.12 python test.py 2>&1 | tail -4
```

Expected: `Ran 134 tests` … `OK`.

- [ ] **Step 9: Commit**

```bash
git add account/dialogs.py
git commit -m "feat(account): sign in with a passkey from the account dialog" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Dialog — passkey sign-up, recovery and management links

**Files:**
- Modify: `constants.py:197-198`
- Modify: `account/dialogs.py`

The server already serves all three pages; this task only opens them. Passkey sign-up has no token to hand back: the account stays inactive until the emailed link is opened, and the user then signs in with the passkey button. The management page signs in on its own; the app does not carry its token into the browser.

- [ ] **Step 1: Constants**

In `constants.py`, replace:

```python
ACCOUNT_BASE_URL = 'https://data.etipitaka.com'
ACCOUNT_CFG = os.path.join(CONFIG_PATH, 'account.cfg')
```

with:

```python
ACCOUNT_BASE_URL = 'https://data.etipitaka.com'
ACCOUNT_CFG = os.path.join(CONFIG_PATH, 'account.cfg')
# Browser-only account pages. Passkey ceremonies run only in a browser on the
# server's own origin, so the app opens these rather than reimplementing them.
ACCOUNT_SIGNUP_URL = ACCOUNT_BASE_URL + '/signup/'
ACCOUNT_PASSKEYS_URL = ACCOUNT_BASE_URL + '/account/security/'
ACCOUNT_RECOVER_URL = ACCOUNT_BASE_URL + '/password_reset/'
```

All three were checked against production on 2026-09-18. `/signup/` and `/password_reset/` return 200. `/account/security/` redirects to `/login/?next=/account/security/`, as it should for a signed-out browser.

- [ ] **Step 2: Import `constants` in the dialog**

In `account/dialogs.py`, replace:

```python
from account.client import AccountError
from account.pairing import PairingSession, DENIED, EXPIRED
```

with:

```python
import constants
from account.client import AccountError
from account.pairing import PairingSession, DENIED, EXPIRED
```

- [ ] **Step 3: Sign-up and recovery buttons on the signed-out screen**

In `_render_logged_out`, replace:

```python
        self._actionButtons = [btnPasskey, btnLogin, btnSignup, btnClose]
```

with:

```python
        btnPasskeySignup = wx.Button(self._panel,
                                     label=u'สมัครสมาชิกด้วยพาสคีย์...')
        btnRecover = wx.Button(self._panel,
                               label=u'ลืมรหัสผ่าน / พาสคีย์หาย...')
        btnPasskeySignup.Bind(wx.EVT_BUTTON, self._on_passkey_signup)
        btnRecover.Bind(wx.EVT_BUTTON, self._on_recover)
        # Stacked, not side by side: two Thai labels this long do not fit
        # across 420px on every platform's default font.
        linkCol = wx.BoxSizer(wx.VERTICAL)
        linkCol.Add(btnPasskeySignup, 0, wx.EXPAND | wx.BOTTOM, 4)
        linkCol.Add(btnRecover, 0, wx.EXPAND)

        self._actionButtons = [btnPasskey, btnLogin, btnSignup, btnClose,
                               btnPasskeySignup, btnRecover]
```

and replace the last line of `_render_logged_out`:

```python
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)

    def _render_logged_in(self):
```

with:

```python
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(linkCol, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _render_logged_in(self):
```

- [ ] **Step 4: Manage passkeys on the signed-in screen**

In `_render_logged_in`, replace:

```python
        btnManage.Bind(wx.EVT_BUTTON, self._on_manage)
```

with:

```python
        btnManage.Bind(wx.EVT_BUTTON, self._on_manage)
        btnPasskeys = wx.Button(self._panel, label=u'จัดการพาสคีย์...')
        btnPasskeys.Bind(wx.EVT_BUTTON, self._on_manage_passkeys)
```

replace:

```python
        actions.Add(btnManage, 0, wx.EXPAND)
```

with:

```python
        actions.Add(btnManage, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnPasskeys, 0, wx.EXPAND)
```

and replace:

```python
        self._actionButtons = [btnUpload, btnDownload, btnManage, btnLogout, btnClose]
```

with:

```python
        self._actionButtons = [btnUpload, btnDownload, btnManage, btnPasskeys,
                               btnLogout, btnClose]
```

- [ ] **Step 5: The three handlers**

Insert directly after `AccountDialog._on_manage`, anchored on this unique block:

```python
    def _on_manage(self, _evt):
        dlg = BackupListDialog(self, self._client, self._presenter)
        dlg.ShowModal()
        dlg.Destroy()
```

Add after it:

```python
    def _on_passkey_signup(self, _evt):
        # No token comes back: a passkey sign-up leaves the account inactive
        # until the emailed link is opened. The user then signs in here with
        # เข้าสู่ระบบด้วยพาสคีย์.
        self._open_browser(constants.ACCOUNT_SIGNUP_URL)

    def _on_recover(self, _evt):
        self._open_browser(constants.ACCOUNT_RECOVER_URL)

    def _on_manage_passkeys(self, _evt):
        # The page signs in on its own; the app does not carry its token
        # into the browser.
        self._open_browser(constants.ACCOUNT_PASSKEYS_URL)
```

- [ ] **Step 5b: Grow the dialog to fit**

The signed-out screen now stacks seven rows. They fit in 420x380 on macOS with room to spare, and on Windows by estimate. On GTK, Thai lines are taller and buttons are 34px, so the busy signed-out screen likely clips the recovery button, and the user cannot resize the dialog to reveal it. Replace `_relayout` (added in Task 6):

```python
    def _relayout(self):
        self._panel.Layout()
        self.Layout()
```

with:

```python
    def _relayout(self):
        # Grow, never shrink: 420x380 is sized for macOS, and GTK's taller
        # Thai lines and 34px buttons need more on the signed-out screen.
        need, have = self._panel.GetBestSize(), self.GetClientSize()
        if need.width > have.width or need.height > have.height:
            self.SetClientSize((max(need.width, have.width),
                                max(need.height, have.height)))
        self._panel.Layout()
        self.Layout()
```

- [ ] **Step 6: Import check and render smoke check**

```bash
uv run --python /opt/homebrew/bin/python3.12 python -c "import account.dialogs; print('ok')"
```

Expected: `ok`. Then build the dialog in every state without showing it. `webbrowser.open_new` is patched so no real browser opens. Do not commit this script:

```bash
uv run --python /opt/homebrew/bin/python3.12 python - <<'PY'
import os, tempfile
import wx
import account.dialogs as d
from account.client import AccountClient
from account.tokenstore import TokenStore

d.webbrowser.open_new = lambda url: True        # never launch a real browser
app = wx.App(False)
store = TokenStore(os.path.join(tempfile.mkdtemp(), 'account.cfg'))
dlg = d.AccountDialog(None, AccountClient('https://example.invalid', store),
                      store, None)
labels = [b.GetLabel() for b in dlg._actionButtons]
for want in [u'เข้าสู่ระบบด้วยพาสคีย์', u'สมัครสมาชิกด้วยพาสคีย์...',
             u'ลืมรหัสผ่าน / พาสคีย์หาย...']:
    assert want in labels, 'missing on the signed-out screen: %s' % want
print('signed out: ok')
dlg._show_pairing('ABCD-2345', 'https://example.invalid/desktop/?code=ABCD-2345')
assert dlg._pulse.IsRunning(), 'pulse timer not started'
print('pairing: ok')
dlg._cancel_pairing()
dlg._render()
assert not dlg._pulse.IsRunning(), 'pulse timer still running after cancel'
store.set('tok', 'alice')
dlg._render()
assert u'จัดการพาสคีย์...' in [b.GetLabel() for b in dlg._actionButtons]
print('signed in: ok')
dlg.Destroy()
PY
```

Expected: `signed out: ok`, `pairing: ok`, `signed in: ok`, and no traceback.

- [ ] **Step 7: Commit**

```bash
git add constants.py account/dialogs.py
git commit -m "feat(account): open passkey sign-up, recovery and management pages" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Privacy policy and spec amendments

**Files:**
- Modify: `PRIVACY.md`
- Modify: `docs/superpowers/specs/2026-09-18-desktop-passkey-design.md` (append)

- [ ] **Step 1: `PRIVACY.md`**

Replace:

```markdown
_Last updated: 3 June 2026_
```

with:

```markdown
_Last updated: 18 September 2026_
```

Replace the whole "Optional account" section:

```markdown
## Optional account

The app works fully without an account. If you choose to create one, we collect
the **email address, username, and password** you provide, sent to our server
at `data.etipitaka.com` to register and sign you in. Your login token is stored
on your device and removed when you log out.
```

with:

```markdown
## Optional account

The app works fully without an account. If you choose to create one, we collect
the **email address, username, and password** you provide — or, if you sign up
with a passkey instead, the email address and username only — sent to our server
at `data.etipitaka.com` to register and sign you in. Your login token is stored
on your device and removed when you log out.

### Passkeys

A passkey lets you sign in without a password. It is created and kept by your
device or password manager (for example iCloud Keychain, Google Password
Manager or Windows Hello). Its private key never leaves that device or password
manager and is never sent to us. Our server stores the matching public key and
the technical details your device reports with it — an identifier for the
passkey, the kind of device or password manager that holds it, whether it is
backed up, and a usage counter — together with the name you give it and when it
was created and last used.

The app itself never handles a passkey. When you choose to sign in with one, it
opens `data.etipitaka.com` in your web browser, the browser performs the passkey
check, and the app then receives the same login token a password sign-in gives.
To link the two, the app shows a short one-time code that you confirm in the
browser. The code expires after ten minutes, and the sign-in request stores no
information about your computer.
```

- [ ] **Step 2: Spec amendments**

Append to the end of `docs/superpowers/specs/2026-09-18-desktop-passkey-design.md`:

```markdown

## Amendments after the server shipped

Written 2026-09-18, after the server half was built, deployed and verified live.
The client plan (`docs/superpowers/plans/2026-09-18-desktop-passkey-client.md`)
follows these where they differ from the sections above.

- **Labels use พาสคีย์, not "Passkey".** The browser confirmation page asks
  `คุณเพิ่งกด "เข้าสู่ระบบด้วยพาสคีย์" บนคอมพิวเตอร์ใช่ไหม?`, quoting the
  desktop button by name, and the site spells the word พาสคีย์ throughout.
  The app's button must match it exactly.
- **Closing the window cancels a pairing instead of being vetoed.** A pairing
  can last ten minutes, and a close button that does nothing that long reads
  as a hang. `cancel()` guarantees no callback reaches the dialog afterwards,
  which is all the veto protects.
- **The poll loop handles two responses the design above omits.** A **429** is
  not a failure: the pairing is still live, so the client backs off by the
  `Retry-After` header (both of the server's limiters send it, with different
  bodies) and never polls faster than `interval`. A **400** ends the session as
  expired — including when an approval's response was lost in transit, because
  the server delivers the token at most once.
- **The token is stored on the UI thread, only if the session was not
  cancelled.** A cancel that races an approval leaves the app signed out; the
  consumed pairing is simply gone.
- **A token that cannot be stored still ends the session.** Storing runs on
  the UI thread, outside the worker's catch-all, so a full disk or a read-only
  config directory reports a failure instead of leaving the dialog waiting.
- **Only a 400 ends a pairing.** Every other error is retried with backoff
  like a network failure: a 5xx during maintenance, and a 200 whose body is
  not a JSON object.
- **Errors do not all reuse `_show_error`.** Its 401 and 404 wording is about
  sessions and backups, so a 404 on begin would read "backup not found". Only
  network failures go through it. Refusal and expiry have their own messages,
  and anything else says the passkey sign-in failed, then why, naming a 5xx as
  `HTTP N` because its body is usually a proxy's HTML page.
- **Esc cancels a pairing**, the same as its Cancel button.
- **Rate limits** are a dedicated nginx zone (120 r/m, burst 60) plus a DRF
  scope at 90/min, not the shared passkey zone proposed above.
- **No language cookie.** Server messages are Thai unless the
  `django_language` cookie says otherwise, and `Accept-Language` is ignored.
  This dialog is hardcoded Thai, so the default is right; localising the dialog
  later would mean sending that cookie.
```

- [ ] **Step 3: Commit**

```bash
git add PRIVACY.md docs/superpowers/specs/2026-09-18-desktop-passkey-design.md
git commit -m "docs: passkeys in the privacy policy; spec amendments after the server shipped" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Full suite, registration integrity, knowledge graph

**Files:** none changed except `graphify-out/` (by the tool)

- [ ] **Step 1: Full suite**

```bash
uv run --python /opt/homebrew/bin/python3.12 python test.py 2>&1 | tail -4
```

Expected: `Ran 134 tests` … `OK` (97 before + 12 client + 25 pairing). Read the output; the exit code means nothing here.

- [ ] **Step 2: Every new test is registered**

Run the `suite()` check from *Before you start* for both modules:
- `tests.test_account_client` → `suite() lists 27 of 27 test methods`
- `tests.test_account_pairing` → `suite() lists 25 of 25 test methods`

- [ ] **Step 3: Nothing stray is staged or committed**

```bash
git status --short
git diff --name-only master...HEAD
```

Expected: `git status` shows only what predates this work — ` M uv.lock` and untracked `.serena/`, `.venv-x86/`, `db_patch.toml`, `patches/`. The branch diff lists only `account/client.py`, `account/dialogs.py`, `account/pairing.py`, `constants.py`, `test.py`, the two test modules, `PRIVACY.md`, and the two docs under `docs/superpowers/`. No `*.sqlite`.

- [ ] **Step 4: Update the knowledge graph**

`CLAUDE.md` asks for a graph update after structural changes, and `account/pairing.py` is a new module:

```bash
graphify update .
```

(`graphify update .` is the CLI form of `CLAUDE.md`'s `graphify . --update`. It re-extracts code only and needs no LLM. If `graphify-out/.graphify_root` changes only from `/Users/sutee/Works/...` to `/Volumes/SeagateBackup/Works/...`, restore it with `git checkout -- graphify-out/.graphify_root`: the first is a symlink to the second.)

Then commit whatever it changed under `graphify-out/`:

```bash
git add graphify-out
git commit -m "chore(graphify): index account/pairing.py" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

If `git status` shows no changes under `graphify-out/`, skip the commit.

---

### Task 10: Manual verification against production

**Files:** none

This task needs a human. The passkey sign-in in the browser uses the tester's own account and device, and the agent must not perform it. The agent runs the app and watches; the human signs in and presses the browser buttons.

- [ ] **Step 1: Run from source (macOS)**

```bash
uv run --python /opt/homebrew/bin/python3.12 python run.py
```

Open the account dialog with the **Account** button in the toolbar. If a previous session is signed in, sign out first.

- [ ] **Step 2: Approve**

1. The signed-out screen shows **เข้าสู่ระบบด้วยพาสคีย์** above the username/password form, and **สมัครสมาชิกด้วยพาสคีย์...** and **ลืมรหัสผ่าน / พาสคีย์หาย...** below it. No label is clipped.
2. Press **เข้าสู่ระบบด้วยพาสคีย์**. The dialog switches to the pairing screen and shows a code like `K7QP-4M2X` in large type. The gauge keeps moving, and the default browser opens `https://data.etipitaka.com/desktop/?code=…` with that code.
3. Sign in with a passkey in the browser. The confirmation page shows the **same code** and asks `คุณเพิ่งกด "เข้าสู่ระบบด้วยพาสคีย์" บนคอมพิวเตอร์ใช่ไหม?`. That button name matches the one just pressed in the app.
4. Press **ใช่ อนุญาต**. Within about 5 seconds the app shows `เข้าสู่ระบบ: <your username>`, and the Dock icon bounces.
5. Press **จัดการข้อมูลสำรอง...**. The backup list loads. This proves the token the pairing stored works for sync.

- [ ] **Step 3: Refuse**

Sign out, press **เข้าสู่ระบบด้วยพาสคีย์** again, and in the browser press **ไม่ใช่**. Expected: within about 5 seconds the app returns to the signed-out screen and shows `คำขอเข้าสู่ระบบถูกปฏิเสธในเบราว์เซอร์`.

- [ ] **Step 4: Cancel and close**

1. Start a pairing and press **ยกเลิก**. Expected: back to the signed-out screen at once. If the pairing is then approved in the browser anyway, the app stays signed out.
2. Start a pairing and close the window with its title-bar close button. Expected: it closes immediately, with no hang and no crash. Reopen the dialog; it works.
3. Start a pairing, close the browser tab, and press **เปิดเบราว์เซอร์อีกครั้ง**. Expected: the same page opens again with the same code.
4. Start a pairing and press **Esc**. Expected: the same as **ยกเลิก**: back to the signed-out screen, and the dialog stays open.

- [ ] **Step 5: Links**

- **สมัครสมาชิกด้วยพาสคีย์...** opens `/signup/`
- **ลืมรหัสผ่าน / พาสคีย์หาย...** opens `/password_reset/`
- While signed in, **จัดการพาสคีย์...** opens `/account/security/`, which asks the browser to sign in on its own

- [ ] **Step 6: Password sign-in is unchanged**

Sign out and sign in with username and password. Expected: works exactly as before.

- [ ] **Step 7: Windows and Linux**

Repeat Steps 2 and 4 on Windows and Linux builds, if available. On Linux, the signed-out screen must show **ลืมรหัสผ่าน / พาสคีย์หาย...** in full, including while signing in with a password (the gauge adds a row); the dialog grows to fit rather than clipping it. On Windows, **ยกเลิก** matters most: its click handler re-renders the dialog, destroying the button whose event is being handled. That was verified safe on macOS only. On Linux, watch the gauge on the pairing screen specifically: it must keep moving for the whole wait, because a single `Pulse()` only moves one step on GTK. Record any platform that is not checked, rather than marking it verified.

---

## After this plan

Release goes through the project's `full-release` skill: version bump, CI builds for Windows and Linux, signed and notarized macOS builds, then the website. That flow has its own human gates (changelog and final confirmation) and is deliberately not part of this plan.

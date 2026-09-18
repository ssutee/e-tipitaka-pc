# Desktop passkey sign-in — design

Date: 2026-09-18
Repos: `E-Tipitaka-PC` (client), `data-etipitaka` (server)
Related: `docs/superpowers/specs/2026-05-23-account-sync-design.md` (the account
subsystem this extends), and in the iOS repo
`docs/superpowers/specs/2026-09-17-native-passkeys-design.md`.

## Goal

Bring passkey sign-in, sign-up, management and recovery to the wxPython desktop
app, matching what `data.etipitaka.com` and the iOS app already support.

## The constraint that drives everything

The server accepts exactly one WebAuthn origin
(`app/user_data/passkey_config.py`):

```python
def expected_origins():
    # iOS native apps report https://<rp id>, so the web origin covers them.
    return [web_origin()] + [android_origin(fp) for fp in settings.PASSKEY_ANDROID_CERT_SHA256]
```

With Android unset in production that list is exactly
`["https://data.etipitaka.com"]`. RP ID is `data.etipitaka.com`.

WebAuthn origins are minted by the OS or the browser. iOS can post credential
JSON straight to the API only because the `webcredentials:data.etipitaka.com`
entitlement makes Apple report that origin. **Python has no equivalent**, so a
wxPython process cannot produce a credential the server will accept.

Therefore the ceremony must happen somewhere that legitimately owns the origin —
the system browser — and the resulting token must be handed back to the app.
The existing web path `/login/passkey/` returns a *session cookie*, not a token,
and its `next=` parameter only accepts safe same-site paths, so there is no way
to bounce a token to the app today. That gap is what this design fills.

Rejected alternatives:

- **Native per-OS ceremony.** macOS could work via pyobjc + `ASAuthorization`,
  but needs an associated-domains entitlement (hence an embedded provisioning
  profile in a Developer ID PyInstaller build) plus the Mac app ID added to
  `PASSKEY_IOS_APP_IDS`. Windows would need ctypes bindings to `webauthn.dll`;
  Linux has nothing. Three implementations, asymmetric UX, high cost.
- **Embedded WebView.** `wx.html2.WebView` maps to WKWebView / WebView2 /
  WebKitGTK, whose platform-authenticator support is inconsistent to absent.
  Too fragile for the primary sign-in path.
- **Loopback redirect.** Snappy and machine-bound, but binds a local port —
  which can raise a Windows Firewall prompt on first run for a non-technical
  audience — and needs a loopback allowlist in the server's redirect validator.

## Architecture

Device-authorization pairing (RFC 8628 in shape, not in wire format — the
wire format follows this codebase's DRF conventions instead).

```
PC app                         Browser                     Server
  |                               |                           |
  |-- POST /desktop/begin/ ------------------------------->   |
  |<-- {device_code, user_code, verification_url} ---------   |
  |                                                           |
  |  show user_code, open browser(verification_url)           |
  |------------------------------>|                           |
  |                               |-- existing passkey login->|
  |                               |   (/login/ + passkey.js)  |
  |                               |-- confirm user_code ----->|
  |                               |   bind pairing -> user    |
  |                                                           |
  |-- POST /desktop/poll/ {device_code}  (every 5s) ------->  |
  |<-- {"status":"approved","key":"<token>","username":"…"} - |
  |                                                           |
  store token -> the existing sync layer works unchanged
```

The passkey ceremony itself is **the web flow already shipped**. Nothing about
`/login/passkey/`, `passkey_login.js` or the verification logic changes.

Two properties make the client side cheap:

1. Passkey login returns the **same DRF token** password login returns
   (`Token.objects.get_or_create`, `passkey_views.py:120`). Once the app holds a
   token, every existing sync call works untouched.
2. Login is username-less / discoverable — the client never sends a username.

## Server (data-etipitaka)

### Model `DesktopPairing`

| Field | Notes |
|---|---|
| `device_code_hash` | sha256 of the device code. The secret itself is never stored. |
| `user_code` | 8 chars, unique among non-expired rows |
| `status` | `pending` / `approved` / `denied` |
| `user` | FK, null until approved |
| `created_at`, `expires_at` | TTL 600s, from a new `PASSKEY_DESKTOP_TTL` setting |

Purged on the same schedule and with the same race-safe criteria as
`PasskeyChallenge` (`app/user_data/passkey_challenges.py`).

`device_code` = `secrets.token_urlsafe(32)` — 43 chars, the same shape as the
existing `challenge_id`. It is the app's secret and is never displayed.

`user_code` = 8 characters drawn from `23456789ABCDEFGHJKMNPQRSTVWXYZ`
(Crockford-style, no `0/O/1/I`), rendered `K7QP-4M2X`. ~39 bits, ample for a
600-second window. Generated with retry on collision against live rows.

### Endpoints

Both follow the house style of `app/user_data/passkey_views.py`: the `_body()`
guard so a non-object body is a clean 400, DRF `Response`, Thai messages.

| Method + path | Auth | Body | Success |
|---|---|---|---|
| `POST /api/passkeys/desktop/begin/` | none | `{}` | `200 {device_code, user_code, verification_url, interval: 5, expires_in: 600}` |
| `POST /api/passkeys/desktop/poll/` | none | `{device_code}` | `200 {"status":"pending"}` · `200 {"status":"approved","key":"<token>","username":"<name>"}` · `200 {"status":"denied"}` |

`poll` returns `400 {"detail": …}` for an unknown, expired or already-consumed
device code. An approved row is **single-use**: it is deleted on the poll that
returns the token.

`verification_url` is `https://data.etipitaka.com/desktop/?code=K7QP-4M2X`.

Returning `username` beside `key` is deliberate. The iOS client has to follow
its login with `GET /rest-auth/user/` purely to learn the username, discarding
the token if that call fails, because it cannot store a token without one. The
PC app has the same requirement, so the server supplies it and saves the
round-trip.

### Confirm page

`GET /desktop/` and `POST /desktop/approve/` — session auth, CSRF-protected,
consistent with the other web views in `passkey_web_views.py`.

- Not signed in → redirect to `/login/?next=/desktop/`. That page already offers
  passkey sign-in, so the ceremony is the existing one.
- Signed in → show the code large, name the account being used
  (`เข้าสู่ระบบในชื่อ <username>` — so a user signed in as the wrong account
  notices before approving), and ask
  `รหัสบนคอมพิวเตอร์ของคุณคือ K7QP-4M2X หรือไม่?` with อนุญาต / ไม่ใช่.
- The page leads with `คุณเพิ่งกด "เข้าสู่ระบบด้วย Passkey" บนคอมพิวเตอร์ใช่ไหม?`
  A user who did not start anything should press ไม่ใช่.
- Approve binds the row to `request.user` and sets `status=approved`. Deny sets
  `status=denied`; the row is deleted once polled.

### Security decisions

- **Phishing.** The confirmation code is the defence: an attacker's pairing
  session shows a different code from the one on the user's screen. Because the
  app opens the URL itself, the honest flow never involves clicking a link from
  elsewhere.
- **The code is prefilled in the URL.** This is RFC 8628's
  `verification_uri_complete`, and it does weaken the check — a phishing link
  prefills the attacker's code too, so the user cannot catch it by comparison
  alone. It is accepted here in exchange for not making every user type eight
  characters, and mitigated by the explicit "did *you* start this?" framing and
  by naming the account. Forcing manual entry is the stricter alternative and
  remains a one-line change if abuse ever appears.
- **Rate limits.** Add `/api/passkeys/desktop/` to the existing passkey zone in
  `nginx/nginx.conf` (60 r/min, burst 30). A 5-second poll interval is 12/min,
  well inside budget.
- **Token lifetime is unchanged** — the DRF token this mints is the same
  non-expiring token password login issues, revoked by `/rest-auth/logout/`.

### Tests

Follow the conventions already in that repo: unit tests for the pairing service
(issue, approve, deny, expiry, single-use, code collision), golden snapshots for
both endpoints with the codes masked, an addition to `tests/passkey_e2e.py`
covering begin → approve → poll, and Thai translations for the new page and
error strings.

## Client (E-Tipitaka-PC)

**No new dependencies.** `requests` plus stdlib `threading` and `webbrowser`.
`etipitaka.spec`'s hand-maintained `hiddenimports` is therefore untouched — a
new C-extension dependency would have been a frozen-build hazard.

### `account/client.py` — two methods appended

```python
desktop_begin()            # -> {device_code, user_code, verification_url, interval, expires_in}
desktop_poll(device_code)  # -> {status, key?, username?}
```

They use bare `requests.post` like every other method in the file, so the
existing test idiom (`@patch('account.client.requests.post')`) extends without
change.

### `account/pairing.py` — new

`PairingSession` owns the worker thread and the poll loop, and imports no wx —
mirroring how `client.py` stays UI-free:

```python
PairingSession(client, on_code, on_done, on_error, dispatch=wx.CallAfter,
               sleep=time.sleep, now=time.monotonic)
```

The injected `dispatch` is what makes it testable: tests pass
`dispatch=lambda fn, *a: fn(*a)` with a fake clock and the whole state machine
runs instantly and headlessly. The dialog passes `wx.CallAfter`.

Loop rules:

- Poll every server-supplied `interval` (default 5s).
- Stop at `expires_in` and report a timeout.
- `denied` reports an error.
- Transient network failures are retried with backoff rather than aborting —
  the browser leg is slow and a single dropped request should not kill a live
  session. Three consecutive failures ends it.
- `cancel()` sets an `Event`, and no callback fires after cancellation. It stops
  polling locally and does not notify the server; if the user then approves in
  the browser anyway, the row is simply never polled and expires within its TTL.

This is added alongside `_run_in_thread` rather than replacing it: that helper
delivers a single result with no cancellation and three existing flows depend on
it. Different lifecycle, separate unit.

On approval the session does `store.clear()` and then
`store.set(token, username)` — the same ordering as `client.login()`
(`account/client.py:51`). Skipping the clear would leak a previous account's
`last_upload` into the new session.

### `account/dialogs.py` — a third render state

`AccountDialog` already re-renders itself in place, so this fits its existing
shape.

| State | Change |
|---|---|
| `_render_logged_out()` | `เข้าสู่ระบบด้วย Passkey` as the primary action above the existing username/password form; `สมัครสมาชิกด้วย Passkey`; `ลืมรหัสผ่าน / Passkey หาย` |
| `_render_pairing()` (new) | the code shown large, a pulsing `wx.Gauge`, `กำลังรอการยืนยันในเบราว์เซอร์...`, `ยกเลิก` |
| `_render_logged_in()` | `จัดการ Passkey` |

Password sign-in is unchanged and stays — it is the fallback, and every existing
user has one. `EVT_CLOSE` vetoes while a pairing is in flight, matching the
existing pattern at `account/dialogs.py:372`. Errors reuse `_show_error`; the
server already replies in Thai, which matches this dialog's hardcoded Thai
strings.

### Browser targets

Three constants beside `ACCOUNT_BASE_URL` in `constants.py`. All three pages
exist today and need no server work:

| Action | URL |
|---|---|
| Sign up with passkey | `https://data.etipitaka.com/signup/` (renders "Create account with a passkey" when supported) |
| Manage passkeys | `https://data.etipitaka.com/account/security/` |
| Recover / lost passkey | `https://data.etipitaka.com/password_reset/` |

Sign-up is a fire-and-forget browser open: `signup/finish` returns
`201 {"detail": "Verification e-mail sent."}` and the account stays inactive
until the emailed link is opened, so there is no token to hand back. After
verifying, the user returns to the app and signs in with the pairing flow.
Managing passkeys on the web requires its own sign-in on that page; the app does
not attempt to carry its token into the browser.

### Tests

`tests/test_account_pairing.py` (new), driving `PairingSession` with a fake
client, fake clock and direct dispatch:

- pending → pending → approved stores token and username
- approved does `clear()` before `set()`
- denied reports an error
- expiry reports a timeout
- `cancel()` stops polling and fires no further callbacks
- a transient network error is retried and the session recovers
- three consecutive failures end the session

Plus `desktop_begin` / `desktop_poll` request and response shapes added to
`tests/test_account_client.py`.

Registration follows the repo's three-edit pattern in `test.py` (import, `suiteN
= …`, add to the `TestSuite` list). Every new test method name must also be
added to the module's `suite()` list, which enumerates names as string literals
— a method missing from it silently never runs.

`account/dialogs.py` has no test coverage anywhere in the repo and no wx-level
tests exist. Keeping all logic in `pairing.py` is what holds that untested
surface thin; the dialog itself gets manual verification on macOS, Windows and
Linux, as in the account-sync plan's Task 7.

### Documentation

`PRIVACY.md` currently describes only the email/username/password model and the
login token. It needs a passkey paragraph: what a passkey is, that the private
key never leaves the user's device or password manager, and that the app itself
performs no cryptographic ceremony — the browser does.

## Non-goals

- Native `ASAuthorization` / pyobjc / `webauthn.dll` ceremonies.
- Migrating the token store to an OS keyring. The token is plaintext JSON in
  `account.cfg` today (`0600` on POSIX, default ACLs on Windows); this feature
  does not make that worse. Worth its own task.
- In-app passkey management UI. The web page already does it.
- QR codes or cross-device pairing. The browser opens on the same machine.

## Rollout order

1. Build, test and deploy the server half. The client cannot be verified
   end-to-end until these endpoints are live, and native passkeys cannot be
   tested against `localhost` — the association files need real HTTPS.
2. Build the PC client against the live endpoints.
3. Manual verification on macOS, Windows and Linux.
4. Version bump and release through the usual `full-release` flow.

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
- **Of the errors, only a 400 ends a pairing.** Every other error is retried
  with backoff like a network failure: a 5xx during maintenance, and a 200
  whose body is not a JSON object. (A readable response the client does not
  understand, such as an unknown status, ends it at once as a failure.)
- **Errors do not all reuse `_show_error`.** Its 401 and 404 wording is about
  sessions and backups, so a 404 on begin would read "backup not found". Only
  network failures go through it. Refusal and expiry have their own messages,
  and anything else says the passkey sign-in failed, then why, naming a 5xx as
  `HTTP N` because its body is usually a proxy's HTML page.
- **Esc cancels a pairing**, the same as its Cancel button.
- **`PairingSession` also takes the token store**, because it stores the token
  itself, and its default `sleep` waits on the cancel event rather than
  `time.sleep`, so `cancel()` wakes the worker at once. `dispatch` is called
  with a single no-argument callable, which suits `wx.CallAfter`.
- **The client opens `verification_url` only if it is on the API's own
  origin.** The app hands it to the OS (`os.startfile` on Windows), so a bad
  begin response must not be able to point it at a file, a network share or
  another app's protocol handler.
- **Rate limits** are a dedicated nginx zone (120 r/m, burst 60) plus a DRF
  scope at 90/min, not the shared passkey zone proposed above.
- **No language cookie.** Server messages are Thai unless the
  `django_language` cookie says otherwise, and `Accept-Language` is ignored.
  This dialog is hardcoded Thai, so the default is right; localising the dialog
  later would mean sending that cookie.

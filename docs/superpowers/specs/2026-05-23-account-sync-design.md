# Account & Cloud Sync

Date: 2026-05-23

## Problem

The E-Tipitaka-PC desktop app has no way to back up user data to a server
or to move it between machines. The iOS sibling app
(`~/Works/obj-c/E-Tipitaka-Plus`) already supports this via accounts on
the existing Django backend (`~/Works/watnapahpong/data-etipitaka`,
host `data.etipitaka.com`). The PC app should gain a comparable feature.

## Goal

Let a signed-in user upload the current PC user data to the backend and
download a previous backup from the backend, replacing the local data
with the downloaded snapshot.

## Scope decisions

- **Backup format:** legacy `.etz` (zip of the whole `DATA_PATH`).
  Reuses the existing `ExportData` zip logic and the existing
  `ImportPCData` extraction logic. The backend tags `.etz` uploads as
  `platform=pc`. No translation to the iOS JSON v3 schema.
- **Sign-up flow:** in-app form. The dialog collects email + username +
  password and calls `POST /rest-auth/registration/`. Email verification
  still happens via the link the server emails.
- **Sync semantics:** manual. The user clicks Upload to push, Download to
  pull. No auto-sync on launch/exit.
- **UI surface:** a single Account dialog with two visual states
  (logged-out and logged-in). Entry point: a new bitmap button on the
  Search view top toolbar, next to the existing Export / Import buttons.
- **Out of scope:** auto-sync, merge of remote into local, sharing
  between users, iOS JSON v3 import/export changes, password reset UI
  inside the app.

## Backend endpoints used

All under `https://data.etipitaka.com`. Authenticated calls send
`Authorization: Token <token>`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/rest-auth/registration/` | POST | Sign up (email, username, password1, password2) |
| `/rest-auth/login/` | POST | Log in (username, password) → `{ key }` |
| `/rest-auth/logout/` | POST | Revoke current token |
| `/rest-auth/user/` | GET | Current user `{ pk, username, email }` |
| `/upload/` | POST multipart | Upload `.etz` (`title`, `file`) |
| `/user_data_list/` | GET | List backups (`items` is a JSON-encoded string) |
| `/user_data/<pk>/` | GET | Download a backup |
| `/user_data/<pk>/` | DELETE | Soft-delete a backup |

`/upload/` infers platform from the filename extension; `.etz` → `pc`.

## Approach

Thin module with clean boundaries: HTTP, token storage, and UI live in
separate files. Existing zip / import logic in `search/presenter.py` is
refactored once so the cloud flow can reuse it without duplicating code.
Background HTTP runs on a worker thread; results re-enter the wx main
thread via `wx.CallAfter`.

Chosen over a full MVP/MVI split (heavier boilerplate for a small
feature) and a single monolithic `account.py` (tangled and hard to test).

## File structure

New package:

```
account/
  __init__.py
  client.py        # AccountClient — requests-based HTTP wrapper
  tokenstore.py    # TokenStore — persists {token, username, last_upload}
  dialogs.py       # AccountDialog, SignUpDialog, BackupListDialog
```

New constants in `constants.py`:

```python
ACCOUNT_BASE_URL = 'https://data.etipitaka.com'
ACCOUNT_CFG      = os.path.join(CONFIG_PATH, 'account.cfg')
```

New entry on the Search view toolbar (`widgets/__init__.py` `SearchToolPanel`):
`AccountButton`, a `wx.BitmapButton` placed next to `ExportButton` /
`ImportButton`. Click opens `AccountDialog`.

Targeted refactor in `search/presenter.py`:
- Split `ExportData()` into `_BuildBackupZip(out_path)` (pure, no UI) and
  the existing file-dialog wrapper that calls it.
- Keep `ImportPCData(path)` / `ImportIOSData(path)` / `ImportAndroidData(path)`
  unchanged — they are already path-based.

New dependency in `pyproject.toml`:

```
requests >= 2.31
```

## Components

### 1. `account/client.py` — `AccountClient`

```python
class AccountError(Exception):
    def __init__(self, status: int, message: str): ...

class AccountClient:
    def __init__(self, base_url: str, tokenstore: TokenStore): ...

    # auth
    def login(self, username: str, password: str) -> str  # returns token
    def register(self, email: str, username: str, password: str) -> None
    def logout(self) -> None
    def current_user(self) -> dict  # {pk, username, email}

    # backups
    def upload(self, etz_path: str, title: str) -> dict       # {success, pk}
    def list_backups(self, platform: str | None = None) -> list[dict]
    def download(self, pk: int) -> bytes
    def delete_backup(self, pk: int) -> None
```

- All authenticated calls add `Authorization: Token <token>` from `tokenstore`.
- Non-2xx responses raise `AccountError(status, server_message)`. Server
  message is the response JSON's `detail` / `non_field_errors[0]` if
  present, else the body text.
- `list_backups` parses the response's `items` field (a JSON-encoded
  Django serializer string) into a list of `{pk, file, platform, created_at}`,
  filtered to `platform` when given. `Download latest` calls with
  `platform='pc'`; `Manage backups...` calls with no filter to show
  every platform.
- `upload` opens the file in binary, posts multipart form data with two
  fields: `title` (string) and `file` (file object). `requests`
  generates the boundary.

### 2. `account/tokenstore.py` — `TokenStore`

```python
class TokenStore:
    def __init__(self, path: str = constants.ACCOUNT_CFG): ...
    def get(self) -> dict | None                # {token, username, last_upload?}
    def set(self, token: str, username: str): ...
    def set_last_upload(self, iso_timestamp: str): ...
    def clear(self): ...
    def is_logged_in(self) -> bool
```

- JSON file at `ACCOUNT_CFG`.
- On POSIX the file is `chmod 0600` after write.
- Missing or unreadable file is treated as logged-out.

### 3. `account/dialogs.py`

- `AccountDialog(parent, client, tokenstore, presenter)` — two visual
  states swapped by `tokenstore.is_logged_in()`:

  Logged-out:

  ```
  +- Account ----------------+
  |  Signed in: -            |
  |  Username: [_________]   |
  |  Password: [_________]   |
  |  [ Login ] [ Sign up...] |
  |              [ Close ]   |
  +--------------------------+
  ```

  Logged-in:

  ```
  +- Account ------------------+
  |  Signed in: alice          |
  |  Last upload: 22 May 14:30 |
  |  [ Upload to Cloud   ]     |
  |  [ Download latest   ]     |
  |  [ Manage backups... ]     |
  |  [ Logout ]      [ Close ] |
  +----------------------------+
  ```

- `SignUpDialog(parent, client)` — modal. Fields: email, username,
  password, confirm password. Validates locally (passwords match,
  non-empty). On success, message box "Verification email sent to
  &lt;email&gt;" and closes.

- `BackupListDialog(parent, client, presenter)` — `wx.ListCtrl`
  (Date, Filename, Size, Platform). Buttons `[Download]`, `[Delete]`,
  `[Close]`. Double-click row triggers Download. Delete asks for
  confirmation.

- During any in-flight HTTP call, the dialog shows a `wx.Gauge`
  (pulse mode) and disables all action buttons.

### 4. Search view wiring

In `widgets/__init__.py` `SearchToolPanel`: add `self._accountButton =
wx.BitmapButton(...)` with an account icon, exposed via an `AccountButton`
property. In `search/view.py` expose the property at the View level. In
`search/interactor.py` bind `EVT_BUTTON` to a new
`OnAccountButtonClick`. In `search/presenter.py` add an `OpenAccount`
method that constructs `AccountClient` + `TokenStore` (or reuses one
held on the presenter) and opens the `AccountDialog`.

## Data flow

```
Sign up:
  user opens AccountDialog -> clicks Sign up
  -> SignUpDialog collects email, username, password
  -> client.register() POST /rest-auth/registration/
  -> "Verification email sent" message; close
  -> user clicks link in email -> account active
  -> user logs in normally

Login:
  AccountDialog collects username + password
  -> worker thread: client.login() POST /rest-auth/login/
  -> tokenstore.set(token, username)
  -> dialog swaps to logged-in state

Upload:
  user clicks Upload to Cloud
  -> worker thread:
      tmp = tempfile.mkstemp(suffix='.etz')
      presenter._BuildBackupZip(tmp)
      filename = f'backup-{YYYY-MM-DD-HHMMSS}-{username}.etz'
      client.upload(tmp, title=filename)
      tokenstore.set_last_upload(now_iso)
      finally: os.remove(tmp)
  -> dialog updates Last-upload timestamp

Download (latest):
  -> worker thread:
      rows = client.list_backups(platform='pc')
      pk   = row with max created_at
      data = client.download(pk)
      write data to a temp .etz
      presenter.ImportPCData(tmp)
      presenter.RefreshHistoryList(...)        # mirrors existing ImportData
      finally: os.remove(tmp)
  -> "Import complete" message

Manage backups:
  -> client.list_backups()  shown in ListCtrl
  -> Download row: same as Download (latest) but with chosen pk
  -> Delete row: confirm -> client.delete_backup(pk) -> refresh list

Logout:
  -> client.logout() POST /rest-auth/logout/
  -> tokenstore.clear()
  -> dialog swaps to logged-out state
```

## Token store layout

```json
{
  "token": "<40-char>",
  "username": "alice",
  "last_upload": "2026-05-22T14:30:00"
}
```

Stored at `constants.ACCOUNT_CFG` (i.e. `CONFIG_PATH/account.cfg`).

## Error handling

- `AccountClient` raises `AccountError(status, message)` on non-2xx.
- Dialog catches `AccountError` and shows a `wx.MessageBox`:
  - 400 → server message verbatim (e.g. validation errors).
  - 401 → token cleared, dialog reverts to logged-out, "Session expired,
    please log in again".
  - 404 → "Backup not found".
- `requests.exceptions.RequestException` (timeout, DNS, refused) → "Cannot
  reach server; check your internet connection".
- Upload removes the temp `.etz` in `finally` even on failure.
- Download removes the temp `.etz` in `finally` even on failure or
  partial parse.

## Threading

- Every HTTP call runs on a worker thread, never on the wx main thread.
- Implementation: a small helper `RunInThread(work, on_success, on_error)`
  that uses `threading.Thread` + `wx.CallAfter` to deliver results back
  to the dialog. Buttons are disabled and a pulsing `wx.Gauge` is shown
  for the duration.
- `_BuildBackupZip` and `ImportPCData` run on the worker (they touch
  disk, not wx widgets).

## Testing

- `tests/test_account_client.py` — unit tests with `unittest.mock`
  patching `requests`:
  - login: posts `{username, password}` to `/rest-auth/login/`, stores token.
  - register: posts the four fields to `/rest-auth/registration/`.
  - upload: posts multipart with `title` + `file` fields; verifies the
    auth header.
  - list_backups: parses the JSON-encoded `items` string into rows; filters
    by platform.
  - download: returns response bytes.
  - delete_backup: sends DELETE and expects 2xx.
  - 401 response → `AccountError`.
- `tests/test_account_tokenstore.py` — uses `tmp_path` for the cfg
  location; round-trip set / get / clear; POSIX file mode check.
- `tests/test_account_export.py` — `_BuildBackupZip` writes a zip of a
  small fake `DATA_PATH`; assert membership.
- Register the three test modules in `test.py` (suite).
- UI dialogs and the new toolbar button are not unit-tested. Manual
  smoke test: sign up, verify email link, log in, upload, log out,
  log in again, download, confirm the imported data lands.

## Constants and dependencies

- `constants.py`:
  - `ACCOUNT_BASE_URL = 'https://data.etipitaka.com'`
  - `ACCOUNT_CFG = os.path.join(CONFIG_PATH, 'account.cfg')`
- `pyproject.toml`:
  - Add runtime dep: `requests>=2.31`.

## Out of scope (explicit)

- Automatic background sync.
- Conflict resolution / 3-way merge of local + remote.
- Sharing endpoints (`/follower/*`, `/user/*/*`, `/sharing_list/`,
  `/user_list/`).
- Changing the existing iOS JSON v3 import/export support.
- In-app password reset.

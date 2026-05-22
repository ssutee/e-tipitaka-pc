# Account & Cloud Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a token-based account, plus upload / download of the existing `.etz` backup to the data.etipitaka.com Django backend, behind a new Account dialog.

**Architecture:** A new `account/` package with three thin units: `tokenstore.py` (persists `{token, username, last_upload}` JSON), `client.py` (`requests`-based HTTP wrapper with typed errors), and `dialogs.py` (Account, SignUp, BackupList dialogs). Existing `ExportData` is split so the zip step is callable headless; existing `ImportPCData` is reused as-is. HTTP runs on a worker thread; results re-enter the wx main thread via `wx.CallAfter`. Entry point is one new bitmap button on the Search view toolbar.

**Tech Stack:** Python 3.12, wxPython 4.2, `requests`, `unittest`, `uv`.

---

## File Structure

- Create: `account/__init__.py` (empty)
- Create: `account/tokenstore.py`
- Create: `account/client.py`
- Create: `account/dialogs.py`
- Create: `resources/account.png` (icon — copy of `resources/edit-notes.png` as a starter; swap-in later)
- Create: `tests/test_account_tokenstore.py`
- Create: `tests/test_account_client.py`
- Create: `tests/test_account_export.py`
- Modify: `pyproject.toml` (add `requests>=2.31`)
- Modify: `constants.py` (add `ACCOUNT_BASE_URL`, `ACCOUNT_CFG`, `ACCOUNT_IMAGE`)
- Modify: `search/presenter.py` (split `ExportData`; add `OpenAccount`, `BuildBackupZip`)
- Modify: `widgets/__init__.py` (`SearchToolPanel`: add `_accountButton`)
- Modify: `search/view.py` (expose `AccountButton`)
- Modify: `search/interactor.py` (bind `EVT_BUTTON` → `OnAccountButtonClick`)
- Modify: `test.py` (register the three new suites)

---

## Task 1: Project setup — constants, icon, dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `constants.py`
- Create: `resources/account.png`
- Create: `account/__init__.py`

- [ ] **Step 1: Add `requests` runtime dep + run uv sync**

Edit `pyproject.toml`, change the `dependencies` array from:

```toml
dependencies = [
    "wxPython>=4.2.1",
    "pony>=0.7.19",
    "xhtml2pdf>=0.2.16",
    "Pillow>=10.0",
    "appdirs>=1.4.4",
    "packaging>=23.0",
]
```

to:

```toml
dependencies = [
    "wxPython>=4.2.1",
    "pony>=0.7.19",
    "xhtml2pdf>=0.2.16",
    "Pillow>=10.0",
    "appdirs>=1.4.4",
    "packaging>=23.0",
    "requests>=2.31",
]
```

Run: `uv sync --python /opt/homebrew/bin/python3.12`
Expected: `requests` installed, `uv.lock` updated.

- [ ] **Step 2: Copy a starter icon**

Run: `cp resources/edit-notes.png resources/account.png`
Expected: file exists at `resources/account.png` (a dedicated icon can replace it later).

- [ ] **Step 3: Add constants**

In `constants.py`, after the line defining `THEME_CFG` (around line 130), add:

```python
ACCOUNT_BASE_URL = 'https://data.etipitaka.com'
ACCOUNT_CFG = os.path.join(CONFIG_PATH, 'account.cfg')
```

Find the block of `*_IMAGE = os.path.join(RESOURCES_DIR, '...png')` constants. After the existing `NOTES_IMAGE` line, add:

```python
ACCOUNT_IMAGE = os.path.join(RESOURCES_DIR, 'account.png')
```

If you cannot locate the exact `NOTES_IMAGE` line by reading `constants.py`, place `ACCOUNT_IMAGE` in the same block as other `_IMAGE` constants — adjacent to whichever image constants already exist.

- [ ] **Step 4: Create the empty package marker**

Create `account/__init__.py` with a single line:

```python
# Account & cloud-sync package.
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock resources/account.png constants.py account/__init__.py
git commit -m "feat(account): scaffold package, constants, requests dep, icon"
```

---

## Task 2: TokenStore + tests

**Files:**
- Create: `account/tokenstore.py`
- Create: `tests/test_account_tokenstore.py`
- Modify: `test.py` (register suite)

- [ ] **Step 1: Write the failing test**

Create `tests/test_account_tokenstore.py`:

```python
#-*- coding:utf-8 -*-

import json
import os
import stat
import sys
import tempfile
import unittest

from account.tokenstore import TokenStore


class TestTokenStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, 'account.cfg')
        self.store = TokenStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        os.rmdir(self.tmpdir)

    def testEmptyByDefault(self):
        self.assertIsNone(self.store.get())
        self.assertFalse(self.store.is_logged_in())

    def testSetAndGetRoundTrip(self):
        self.store.set('tok123', 'alice')
        self.assertTrue(self.store.is_logged_in())
        data = self.store.get()
        self.assertEqual('tok123', data['token'])
        self.assertEqual('alice', data['username'])

    def testFilePersistsOnDisk(self):
        self.store.set('tok123', 'alice')
        with open(self.path) as f:
            raw = json.load(f)
        self.assertEqual('tok123', raw['token'])
        self.assertEqual('alice', raw['username'])

    def testClearRemovesData(self):
        self.store.set('tok123', 'alice')
        self.store.clear()
        self.assertIsNone(self.store.get())
        self.assertFalse(self.store.is_logged_in())

    def testSetLastUploadPreservesToken(self):
        self.store.set('tok123', 'alice')
        self.store.set_last_upload('2026-05-22T14:30:00')
        data = self.store.get()
        self.assertEqual('tok123', data['token'])
        self.assertEqual('2026-05-22T14:30:00', data['last_upload'])

    def testMissingFileTreatedAsLoggedOut(self):
        store = TokenStore(os.path.join(self.tmpdir, 'does-not-exist.cfg'))
        self.assertIsNone(store.get())
        self.assertFalse(store.is_logged_in())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX file modes only')
    def testFileMode0600OnPosix(self):
        self.store.set('tok123', 'alice')
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(0o600, mode)


def suite():
    s = unittest.TestSuite()
    for name in ['testEmptyByDefault', 'testSetAndGetRoundTrip',
                 'testFilePersistsOnDisk', 'testClearRemovesData',
                 'testSetLastUploadPreservesToken',
                 'testMissingFileTreatedAsLoggedOut',
                 'testFileMode0600OnPosix']:
        s.addTest(TestTokenStore(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_tokenstore -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'account.tokenstore'`.

- [ ] **Step 3: Implement `TokenStore`**

Create `account/tokenstore.py`:

```python
#-*- coding:utf-8 -*-

import json
import os
import sys

import constants


class TokenStore(object):
    """Persist {token, username, last_upload} as JSON at `path`."""

    def __init__(self, path=None):
        self._path = path if path is not None else constants.ACCOUNT_CFG

    def get(self):
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, ValueError):
            return None

    def set(self, token, username):
        data = self.get() or {}
        data['token'] = token
        data['username'] = username
        self._write(data)

    def set_last_upload(self, iso_timestamp):
        data = self.get() or {}
        data['last_upload'] = iso_timestamp
        self._write(data)

    def clear(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def is_logged_in(self):
        data = self.get()
        return bool(data and data.get('token'))

    def _write(self, data):
        parent = os.path.dirname(self._path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        if sys.platform != 'win32':
            os.chmod(self._path, 0o600)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_tokenstore -v`
Expected: PASS — 7 tests OK.

- [ ] **Step 5: Register the suite in `test.py`**

Read the current `test.py`. It imports `tests.test_threads` and `tests.test_theme` and builds a combined suite. Add `tests.test_account_tokenstore` so the final content is:

```python
import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3])

runner = unittest.TextTestRunner()
runner.run(alltests)
```

- [ ] **Step 6: Commit**

```bash
git add account/tokenstore.py tests/test_account_tokenstore.py test.py
git commit -m "feat(account): TokenStore with JSON persistence and 0600 perms"
```

---

## Task 3: AccountClient + tests

**Files:**
- Create: `account/client.py`
- Create: `tests/test_account_client.py`
- Modify: `test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_account_client.py`:

```python
#-*- coding:utf-8 -*-

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from account.client import AccountClient, AccountError
from account.tokenstore import TokenStore


BASE = 'https://data.etipitaka.example'


def _resp(status=200, json_body=None, content=b''):
    r = MagicMock()
    r.status_code = status
    r.ok = 200 <= status < 300
    r.json = MagicMock(return_value=json_body if json_body is not None else {})
    r.content = content
    r.text = json.dumps(json_body) if json_body is not None else content.decode('utf-8', 'ignore')
    return r


class TestAccountClient(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmpdir, 'account.cfg')
        self.store = TokenStore(self.cfg)
        self.client = AccountClient(BASE, self.store)

    def tearDown(self):
        if os.path.exists(self.cfg):
            os.remove(self.cfg)
        os.rmdir(self.tmpdir)

    @patch('account.client.requests.post')
    def testLoginStoresToken(self, post):
        post.return_value = _resp(200, {'key': 'tok123'})
        token = self.client.login('alice', 'pw')
        self.assertEqual('tok123', token)
        post.assert_called_once_with(
            BASE + '/rest-auth/login/',
            json={'username': 'alice', 'password': 'pw'},
            timeout=30,
        )
        self.assertEqual('tok123', self.store.get()['token'])
        self.assertEqual('alice', self.store.get()['username'])

    @patch('account.client.requests.post')
    def testLoginBadCredentialsRaises(self, post):
        post.return_value = _resp(400, {'non_field_errors': ['bad creds']})
        with self.assertRaises(AccountError) as cm:
            self.client.login('alice', 'wrong')
        self.assertEqual(400, cm.exception.status)
        self.assertEqual('bad creds', cm.exception.message)

    @patch('account.client.requests.post')
    def testRegisterPostsFourFields(self, post):
        post.return_value = _resp(201, {'detail': 'Verification e-mail sent.'})
        self.client.register('a@b.c', 'alice', 'pw1234567')
        post.assert_called_once_with(
            BASE + '/rest-auth/registration/',
            json={'email': 'a@b.c', 'username': 'alice',
                  'password1': 'pw1234567', 'password2': 'pw1234567'},
            timeout=30,
        )

    @patch('account.client.requests.post')
    def testLogoutPostsWithAuthHeader(self, post):
        self.store.set('tok123', 'alice')
        post.return_value = _resp(200, {'detail': 'Successfully logged out.'})
        self.client.logout()
        _, kwargs = post.call_args
        self.assertEqual('Token tok123', kwargs['headers']['Authorization'])

    @patch('account.client.requests.get')
    def testCurrentUser(self, get):
        self.store.set('tok123', 'alice')
        get.return_value = _resp(200, {'pk': 1, 'username': 'alice',
                                       'email': 'a@b.c'})
        u = self.client.current_user()
        self.assertEqual('alice', u['username'])

    @patch('account.client.requests.post')
    def testUploadPostsMultipart(self, post):
        self.store.set('tok123', 'alice')
        post.return_value = _resp(200, {'success': True, 'pk': 99})
        with tempfile.NamedTemporaryFile(suffix='.etz', delete=False) as tmp:
            tmp.write(b'zip-bytes')
            path = tmp.name
        try:
            result = self.client.upload(path, 'backup-test.etz')
            self.assertEqual(99, result['pk'])
            args, kwargs = post.call_args
            self.assertEqual(BASE + '/upload/', args[0])
            self.assertEqual('Token tok123', kwargs['headers']['Authorization'])
            self.assertEqual('backup-test.etz', kwargs['data']['title'])
            self.assertIn('file', kwargs['files'])
        finally:
            os.remove(path)

    @patch('account.client.requests.get')
    def testListBackupsParsesItemsJsonString(self, get):
        items_payload = json.dumps([
            {'pk': 1, 'fields': {'platform': 'pc',
                                 'file': 'alice/pc/backup-old.etz',
                                 'created_at': '2026-05-20T00:00:00Z'}},
            {'pk': 2, 'fields': {'platform': 'ios',
                                 'file': 'alice/ios/data.json',
                                 'created_at': '2026-05-21T00:00:00Z'}},
            {'pk': 3, 'fields': {'platform': 'pc',
                                 'file': 'alice/pc/backup-new.etz',
                                 'created_at': '2026-05-22T00:00:00Z'}},
        ])
        get.return_value = _resp(200, {'items': items_payload})
        self.store.set('tok123', 'alice')

        rows = self.client.list_backups(platform='pc')
        self.assertEqual([1, 3], sorted(r['pk'] for r in rows))

        rows_all = self.client.list_backups()
        self.assertEqual(3, len(rows_all))

    @patch('account.client.requests.get')
    def testDownloadReturnsBytes(self, get):
        self.store.set('tok123', 'alice')
        get.return_value = _resp(200, content=b'etzbytes')
        data = self.client.download(99)
        self.assertEqual(b'etzbytes', data)
        args, kwargs = get.call_args
        self.assertEqual(BASE + '/user_data/99/', args[0])

    @patch('account.client.requests.delete')
    def testDeleteBackup(self, delete):
        self.store.set('tok123', 'alice')
        delete.return_value = _resp(200, {'success': True})
        self.client.delete_backup(99)
        args, _ = delete.call_args
        self.assertEqual(BASE + '/user_data/99/', args[0])

    @patch('account.client.requests.get')
    def testUnauthorizedRaisesAccountError(self, get):
        self.store.set('tok123', 'alice')
        get.return_value = _resp(401, {'detail': 'auth required'})
        with self.assertRaises(AccountError) as cm:
            self.client.current_user()
        self.assertEqual(401, cm.exception.status)


def suite():
    s = unittest.TestSuite()
    for name in ['testLoginStoresToken', 'testLoginBadCredentialsRaises',
                 'testRegisterPostsFourFields', 'testLogoutPostsWithAuthHeader',
                 'testCurrentUser', 'testUploadPostsMultipart',
                 'testListBackupsParsesItemsJsonString',
                 'testDownloadReturnsBytes', 'testDeleteBackup',
                 'testUnauthorizedRaisesAccountError']:
        s.addTest(TestAccountClient(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'account.client'`.

- [ ] **Step 3: Implement `AccountClient`**

Create `account/client.py`:

```python
#-*- coding:utf-8 -*-

import json

import requests


class AccountError(Exception):
    def __init__(self, status, message):
        super(AccountError, self).__init__('%d: %s' % (status, message))
        self.status = status
        self.message = message


def _extract_message(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text or ''
    if isinstance(body, dict):
        if 'detail' in body:
            return str(body['detail'])
        if 'non_field_errors' in body and body['non_field_errors']:
            return str(body['non_field_errors'][0])
        for v in body.values():
            if isinstance(v, list) and v:
                return str(v[0])
            if isinstance(v, str):
                return v
    return str(body)


class AccountClient(object):

    def __init__(self, base_url, tokenstore, timeout=30):
        self._base = base_url.rstrip('/')
        self._store = tokenstore
        self._timeout = timeout

    def login(self, username, password):
        resp = requests.post(
            self._base + '/rest-auth/login/',
            json={'username': username, 'password': password},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        token = resp.json()['key']
        self._store.set(token, username)
        return token

    def register(self, email, username, password):
        resp = requests.post(
            self._base + '/rest-auth/registration/',
            json={'email': email, 'username': username,
                  'password1': password, 'password2': password},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)

    def logout(self):
        resp = requests.post(
            self._base + '/rest-auth/logout/',
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        if not resp.ok and resp.status_code != 401:
            self._raise_if_error(resp)

    def current_user(self):
        resp = requests.get(
            self._base + '/rest-auth/user/',
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return resp.json()

    def upload(self, etz_path, title):
        with open(etz_path, 'rb') as f:
            resp = requests.post(
                self._base + '/upload/',
                headers=self._auth_headers(),
                data={'title': title},
                files={'file': (title, f, 'application/octet-stream')},
                timeout=self._timeout,
            )
        self._raise_if_error(resp)
        return resp.json()

    def list_backups(self, platform=None):
        resp = requests.get(
            self._base + '/user_data_list/',
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        raw = resp.json().get('items', '[]')
        items = json.loads(raw) if isinstance(raw, str) else raw
        rows = []
        for it in items:
            fields = it.get('fields', it)
            rows.append({
                'pk': it.get('pk', fields.get('pk')),
                'file': fields.get('file', ''),
                'platform': fields.get('platform', ''),
                'created_at': fields.get('created_at', ''),
            })
        if platform is not None:
            rows = [r for r in rows if r['platform'] == platform]
        return rows

    def download(self, pk):
        resp = requests.get(
            '%s/user_data/%d/' % (self._base, pk),
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return resp.content

    def delete_backup(self, pk):
        resp = requests.delete(
            '%s/user_data/%d/' % (self._base, pk),
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)

    def _auth_headers(self):
        data = self._store.get() or {}
        token = data.get('token')
        if not token:
            raise AccountError(401, 'not logged in')
        return {'Authorization': 'Token ' + token}

    def _raise_if_error(self, resp):
        if not resp.ok:
            raise AccountError(resp.status_code, _extract_message(resp))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_client -v`
Expected: PASS — 10 tests OK.

- [ ] **Step 5: Register the suite in `test.py`**

Add `import tests.test_account_client` and append `tests.test_account_client.suite()` to the `alltests` list. Final `test.py`:

```python
import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore
import tests.test_account_client

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
suite4 = tests.test_account_client.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4])

runner = unittest.TextTestRunner()
runner.run(alltests)
```

- [ ] **Step 6: Commit**

```bash
git add account/client.py tests/test_account_client.py test.py
git commit -m "feat(account): AccountClient HTTP wrapper with typed errors"
```

---

## Task 4: Split `ExportData` so the zip step is callable headless

**Files:**
- Modify: `search/presenter.py`
- Create: `tests/test_account_export.py`
- Modify: `test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_account_export.py`:

```python
#-*- coding:utf-8 -*-

import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch


class TestBuildBackupZip(unittest.TestCase):

    def setUp(self):
        self.dataDir = tempfile.mkdtemp()
        with open(os.path.join(self.dataDir, 'data.sqlite'), 'wb') as f:
            f.write(b'fake-sqlite')
        os.makedirs(os.path.join(self.dataDir, 'notes', 'thai'))
        with open(os.path.join(self.dataDir, 'notes', 'thai', '1-1.xml'), 'wb') as f:
            f.write(b'<note/>')
        self.outDir = tempfile.mkdtemp()
        self.outPath = os.path.join(self.outDir, 'backup-test.etz')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dataDir, ignore_errors=True)
        shutil.rmtree(self.outDir, ignore_errors=True)

    def testBuildBackupZipIncludesAllFiles(self):
        with patch('constants.DATA_PATH', self.dataDir):
            from search.presenter import BuildBackupZip
            BuildBackupZip(self.outPath)
        self.assertTrue(os.path.exists(self.outPath))
        with zipfile.ZipFile(self.outPath) as z:
            names = set(z.namelist())
        self.assertIn('data.sqlite', names)
        self.assertIn(os.path.join('notes', 'thai', '1-1.xml'), names)


def suite():
    s = unittest.TestSuite()
    s.addTest(TestBuildBackupZip('testBuildBackupZipIncludesAllFiles'))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_export -v`
Expected: FAIL — `ImportError` for `BuildBackupZip`, or it does not exist.

- [ ] **Step 3: Refactor `ExportData`**

Open `search/presenter.py`. Locate the current `ExportData` method (around line 273), which reads:

```python
    def ExportData(self):
        from datetime import datetime
        zipFile = 'backup-%s.etz' % (datetime.now().strftime('%Y-%m-%d'))
        dlg = wx.FileDialog(self._view, _('Save data'), constants.HOME, zipFile, constants.ETZ_TYPE, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            with zipfile.ZipFile(os.path.join(dlg.GetDirectory(), dlg.GetFilename()), 'w') as fz:
                rootlen = len(constants.DATA_PATH) + 1
                for base, dirs, files in os.walk(constants.DATA_PATH):
                    for filename in files:
                            fn = os.path.join(base, filename)
                            fz.write(fn, fn[rootlen:])
            wx.MessageBox(_('Export data complete'), 'E-Tipitaka')
        dlg.Destroy()
```

Add a new module-level function near the top of `search/presenter.py` (after the imports, before the `Presenter` class):

```python
def BuildBackupZip(out_path):
    """Write a .etz zip of constants.DATA_PATH to `out_path`. No UI."""
    rootlen = len(constants.DATA_PATH) + 1
    with zipfile.ZipFile(out_path, 'w') as fz:
        for base, dirs, files in os.walk(constants.DATA_PATH):
            for filename in files:
                fn = os.path.join(base, filename)
                fz.write(fn, fn[rootlen:])
```

Then replace the body of `ExportData`:

```python
    def ExportData(self):
        from datetime import datetime
        zipFile = 'backup-%s.etz' % (datetime.now().strftime('%Y-%m-%d'))
        dlg = wx.FileDialog(self._view, _('Save data'), constants.HOME, zipFile, constants.ETZ_TYPE, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            BuildBackupZip(os.path.join(dlg.GetDirectory(), dlg.GetFilename()))
            wx.MessageBox(_('Export data complete'), 'E-Tipitaka')
        dlg.Destroy()
```

`os` and `zipfile` are already imported at the top of `search/presenter.py`; do not add duplicate imports. `constants` is already imported.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_account_export -v`
Expected: PASS — 1 test OK.

- [ ] **Step 5: Register the suite + run full suite**

Add `import tests.test_account_export` and `tests.test_account_export.suite()` to `test.py`. Final:

```python
import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore
import tests.test_account_client
import tests.test_account_export

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
suite4 = tests.test_account_client.suite()
suite5 = tests.test_account_export.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5])

runner = unittest.TextTestRunner()
runner.run(alltests)
```

Run: `uv run --python /opt/homebrew/bin/python3.12 python test.py`
Expected: all previously-passing tests still pass; the new export test passes.

- [ ] **Step 6: Commit**

```bash
git add search/presenter.py tests/test_account_export.py test.py
git commit -m "refactor(search): extract BuildBackupZip from ExportData"
```

---

## Task 5: Account dialogs

**Files:**
- Create: `account/dialogs.py`

GUI module. No unit tests for the dialogs themselves. Next task wires them in.

- [ ] **Step 1: Create the dialogs module**

Create `account/dialogs.py`:

```python
#-*- coding:utf-8 -*-

import os
import tempfile
import threading
from datetime import datetime

import wx

import constants
from account.client import AccountError


def _run_in_thread(work, on_success, on_error):
    """Run `work()` on a worker thread; deliver result via wx.CallAfter."""
    def _target():
        try:
            result = work()
        except AccountError as e:
            wx.CallAfter(on_error, e)
            return
        except Exception as e:
            wx.CallAfter(on_error, AccountError(0, str(e)))
            return
        wx.CallAfter(on_success, result)

    threading.Thread(target=_target, daemon=True).start()


def _show_error(parent, err):
    if err.status == 401:
        msg = 'Session expired, please log in again.'
    elif err.status == 404:
        msg = 'Backup not found.'
    elif err.status == 0:
        msg = 'Cannot reach server; check your internet connection.\n\n%s' % err.message
    else:
        msg = err.message or ('HTTP %d' % err.status)
    wx.MessageBox(msg, 'E-Tipitaka — Account', wx.OK | wx.ICON_ERROR, parent)


class SignUpDialog(wx.Dialog):

    def __init__(self, parent, client):
        super(SignUpDialog, self).__init__(parent, title='Sign up',
                                           size=(360, 260))
        self._client = client

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=4, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)

        self._email = wx.TextCtrl(panel)
        self._username = wx.TextCtrl(panel)
        self._password = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._confirm = wx.TextCtrl(panel, style=wx.TE_PASSWORD)

        for label, ctrl in [('Email', self._email),
                            ('Username', self._username),
                            ('Password', self._password),
                            ('Confirm', self._confirm)]:
            grid.Add(wx.StaticText(panel, label=label),
                     flag=wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        self._btnOk = wx.Button(panel, label='Sign up')
        self._btnCancel = wx.Button(panel, wx.ID_CANCEL, label='Cancel')
        self._btnOk.Bind(wx.EVT_BUTTON, self._on_signup)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnRow.AddStretchSpacer()
        btnRow.Add(self._btnOk, 0, wx.RIGHT, 6)
        btnRow.Add(self._btnCancel, 0)

        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

    def _on_signup(self, _evt):
        email = self._email.GetValue().strip()
        username = self._username.GetValue().strip()
        pw = self._password.GetValue()
        cf = self._confirm.GetValue()
        if not (email and username and pw):
            wx.MessageBox('Email, username and password are required.',
                          'Sign up', wx.OK | wx.ICON_WARNING, self)
            return
        if pw != cf:
            wx.MessageBox('Passwords do not match.', 'Sign up',
                          wx.OK | wx.ICON_WARNING, self)
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.register(email, username, pw),
            on_success=self._on_done(email),
            on_error=self._on_err,
        )

    def _on_done(self, email):
        def _cb(_result):
            self._busy(False)
            wx.MessageBox('Verification email sent to %s.' % email,
                          'Sign up', wx.OK | wx.ICON_INFORMATION, self)
            self.EndModal(wx.ID_OK)
        return _cb

    def _on_err(self, err):
        self._busy(False)
        _show_error(self, err)

    def _busy(self, on):
        self._btnOk.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()


class BackupListDialog(wx.Dialog):

    def __init__(self, parent, client, presenter):
        super(BackupListDialog, self).__init__(parent, title='Manage backups',
                                               size=(560, 360))
        self._client = client
        self._presenter = presenter

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._list.InsertColumn(0, 'Date', width=170)
        self._list.InsertColumn(1, 'Filename', width=240)
        self._list.InsertColumn(2, 'Platform', width=80)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_download)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        self._btnDownload = wx.Button(panel, label='Download')
        self._btnDelete = wx.Button(panel, label='Delete')
        self._btnClose = wx.Button(panel, wx.ID_CLOSE, label='Close')
        self._btnDownload.Bind(wx.EVT_BUTTON, self._on_download)
        self._btnDelete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        btnRow.Add(self._btnDownload, 0, wx.RIGHT, 6)
        btnRow.Add(self._btnDelete, 0, wx.RIGHT, 6)
        btnRow.AddStretchSpacer()
        btnRow.Add(self._btnClose, 0)

        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self._rows = []
        self._refresh()

    def _refresh(self):
        self._busy(True)
        _run_in_thread(
            lambda: self._client.list_backups(),
            on_success=self._on_listed,
            on_error=self._on_err,
        )

    def _on_listed(self, rows):
        self._busy(False)
        self._rows = sorted(rows, key=lambda r: r['created_at'], reverse=True)
        self._list.DeleteAllItems()
        for r in self._rows:
            idx = self._list.InsertItem(self._list.GetItemCount(),
                                        str(r['created_at']))
            self._list.SetItem(idx, 1, os.path.basename(str(r['file'])))
            self._list.SetItem(idx, 2, str(r['platform']))

    def _selected_pk(self):
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return None
        return self._rows[idx]['pk']

    def _on_download(self, _evt):
        pk = self._selected_pk()
        if pk is None:
            return
        self._busy(True)
        _run_in_thread(
            lambda: _download_and_import(self._client, self._presenter, pk),
            on_success=self._on_imported,
            on_error=self._on_err,
        )

    def _on_imported(self, _result):
        self._busy(False)
        wx.MessageBox('Import complete.', 'E-Tipitaka — Account',
                      wx.OK | wx.ICON_INFORMATION, self)

    def _on_delete(self, _evt):
        pk = self._selected_pk()
        if pk is None:
            return
        if wx.MessageBox('Delete this backup permanently?', 'Confirm',
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.delete_backup(pk),
            on_success=lambda _r: self._refresh(),
            on_error=self._on_err,
        )

    def _on_err(self, err):
        self._busy(False)
        _show_error(self, err)

    def _busy(self, on):
        for b in (self._btnDownload, self._btnDelete):
            b.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()


def _download_and_import(client, presenter, pk):
    data = client.download(pk)
    fd, tmp = tempfile.mkstemp(suffix='.etz')
    os.close(fd)
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        presenter.ImportPCData(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _build_and_upload(client, presenter, username):
    from search.presenter import BuildBackupZip
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    filename = 'backup-%s-%s.etz' % (timestamp, username)
    fd, tmp = tempfile.mkstemp(suffix='.etz')
    os.close(fd)
    try:
        BuildBackupZip(tmp)
        client.upload(tmp, filename)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return datetime.now().isoformat(timespec='seconds')


def _download_latest(client, presenter):
    rows = client.list_backups(platform='pc')
    if not rows:
        raise AccountError(404, 'No PC backups found on server.')
    rows.sort(key=lambda r: r['created_at'], reverse=True)
    _download_and_import(client, presenter, rows[0]['pk'])


class AccountDialog(wx.Dialog):

    def __init__(self, parent, client, tokenstore, presenter):
        super(AccountDialog, self).__init__(parent, title='Account',
                                            size=(380, 280))
        self._client = client
        self._store = tokenstore
        self._presenter = presenter

        self._panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._panel.SetSizer(self._sizer)

        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []

        self._render()

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

    def _render_logged_out(self):
        grid = wx.FlexGridSizer(rows=3, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self._panel, label='Signed in: -'))
        grid.Add(wx.StaticText(self._panel, label=''))
        self._username = wx.TextCtrl(self._panel)
        self._password = wx.TextCtrl(self._panel, style=wx.TE_PASSWORD)
        grid.Add(wx.StaticText(self._panel, label='Username'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._username, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self._panel, label='Password'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._password, 1, wx.EXPAND)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnLogin = wx.Button(self._panel, label='Login')
        btnSignup = wx.Button(self._panel, label='Sign up...')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label='Close')
        btnLogin.Bind(wx.EVT_BUTTON, self._on_login)
        btnSignup.Bind(wx.EVT_BUTTON, self._on_signup)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        btnRow.Add(btnLogin, 0, wx.RIGHT, 6)
        btnRow.Add(btnSignup, 0)
        btnRow.AddStretchSpacer()
        btnRow.Add(btnClose, 0)

        self._actionButtons = [btnLogin, btnSignup]

        self._sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)

    def _render_logged_in(self):
        data = self._store.get() or {}
        info = wx.BoxSizer(wx.VERTICAL)
        info.Add(wx.StaticText(self._panel,
            label='Signed in: %s' % data.get('username', '')), 0, wx.BOTTOM, 4)
        last = data.get('last_upload', '-')
        info.Add(wx.StaticText(self._panel, label='Last upload: %s' % last),
                 0, wx.BOTTOM, 4)

        btnUpload = wx.Button(self._panel, label='Upload to Cloud')
        btnDownload = wx.Button(self._panel, label='Download latest')
        btnManage = wx.Button(self._panel, label='Manage backups...')
        btnLogout = wx.Button(self._panel, label='Logout')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label='Close')
        btnUpload.Bind(wx.EVT_BUTTON, self._on_upload)
        btnDownload.Bind(wx.EVT_BUTTON, self._on_download_latest)
        btnManage.Bind(wx.EVT_BUTTON, self._on_manage)
        btnLogout.Bind(wx.EVT_BUTTON, self._on_logout)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))

        actions = wx.BoxSizer(wx.VERTICAL)
        actions.Add(btnUpload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnDownload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnManage, 0, wx.EXPAND)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        bottom.Add(btnLogout, 0)
        bottom.AddStretchSpacer()
        bottom.Add(btnClose, 0)

        self._actionButtons = [btnUpload, btnDownload, btnManage, btnLogout]

        self._sizer.Add(info, 0, wx.ALL, 10)
        self._sizer.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(bottom, 0, wx.EXPAND | wx.ALL, 10)

    def _on_login(self, _evt):
        u = self._username.GetValue().strip()
        p = self._password.GetValue()
        if not (u and p):
            wx.MessageBox('Username and password are required.',
                          'Login', wx.OK | wx.ICON_WARNING, self)
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.login(u, p),
            on_success=lambda _r: (self._busy(False), self._render()),
            on_error=self._on_err,
        )

    def _on_signup(self, _evt):
        dlg = SignUpDialog(self, self._client)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_upload(self, _evt):
        data = self._store.get() or {}
        username = data.get('username', 'user')
        self._busy(True)
        _run_in_thread(
            lambda: _build_and_upload(self._client, self._presenter, username),
            on_success=self._on_uploaded,
            on_error=self._on_err,
        )

    def _on_uploaded(self, iso_timestamp):
        self._store.set_last_upload(iso_timestamp)
        self._busy(False)
        wx.MessageBox('Upload complete.', 'E-Tipitaka — Account',
                      wx.OK | wx.ICON_INFORMATION, self)
        self._render()

    def _on_download_latest(self, _evt):
        self._busy(True)
        _run_in_thread(
            lambda: _download_latest(self._client, self._presenter),
            on_success=lambda _r: (self._busy(False),
                wx.MessageBox('Import complete.', 'E-Tipitaka — Account',
                              wx.OK | wx.ICON_INFORMATION, self)),
            on_error=self._on_err,
        )

    def _on_manage(self, _evt):
        dlg = BackupListDialog(self, self._client, self._presenter)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_logout(self, _evt):
        self._busy(True)
        _run_in_thread(
            lambda: self._client.logout(),
            on_success=lambda _r: (self._store.clear(), self._busy(False),
                                   self._render()),
            on_error=lambda e: (self._store.clear(), self._busy(False),
                                self._render()),
        )

    def _on_err(self, err):
        if err.status == 401:
            self._store.clear()
        self._busy(False)
        _show_error(self, err)
        if err.status == 401:
            self._render()

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

- [ ] **Step 2: Smoke-import the module**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -c "import account.dialogs; print('ok')"`
Expected: `ok` printed.

- [ ] **Step 3: Run the full test suite (no new tests, but make sure nothing regressed)**

Run: `uv run --python /opt/homebrew/bin/python3.12 python test.py`
Expected: all previously-passing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add account/dialogs.py
git commit -m "feat(account): Account / SignUp / BackupList dialogs"
```

---

## Task 6: Wire the Account button into the Search view

**Files:**
- Modify: `widgets/__init__.py` (`SearchToolPanel`)
- Modify: `search/view.py` (expose `AccountButton`)
- Modify: `search/interactor.py` (bind event)
- Modify: `search/presenter.py` (`OpenAccount` method)

- [ ] **Step 1: Add the button to `SearchToolPanel`**

Open `widgets/__init__.py` and find the `SearchToolPanel.ExportButton` and `ImportButton` properties (around line 1821–1828):

```python
    @property
    def ExportButton(self):
        return self._exportButton

    @property
    def ImportButton(self):
        return self._importButton
```

Immediately after `ImportButton`, add:

```python
    @property
    def AccountButton(self):
        return self._accountButton
```

Find where `self._exportButton` and `self._importButton` are constructed inside `SearchToolPanel.__init__` (grep for `self._exportButton =`). Immediately after the construction of `self._importButton` and the line that adds it to its sizer, mirror the same pattern for the new button. Sample of existing construction:

```python
self._exportButton = wx.BitmapButton(self, wx.ID_ANY,
    wx.Bitmap(wx.Image(constants.EXPORT_IMAGE, wx.BITMAP_TYPE_PNG)))
```

Append:

```python
self._accountButton = wx.BitmapButton(self, wx.ID_ANY,
    wx.Bitmap(wx.Image(constants.ACCOUNT_IMAGE, wx.BITMAP_TYPE_PNG)))
self._accountButton.SetToolTip(wx.ToolTip('Account / cloud sync'))
```

And add it to the same sizer holding `_exportButton` and `_importButton`, copying the exact `.Add(...)` flags those buttons use.

- [ ] **Step 2: Expose `AccountButton` from `search/view.py`**

Open `search/view.py`. After the `ImportButton` property (around line 32), add:

```python
    @property
    def AccountButton(self):
        return self._topBar.AccountButton
```

- [ ] **Step 3: Bind the event in the search interactor**

Open `search/interactor.py`. After the existing `self.View.ImportButton.Bind(...)` line, add:

```python
        self.View.AccountButton.Bind(wx.EVT_BUTTON, self.OnAccountButtonClick)
```

Below the existing `OnExportButtonClick` / `OnImportButtonClick` methods, add:

```python
    def OnAccountButtonClick(self, event):
        self.Presenter.OpenAccount()
```

- [ ] **Step 4: Add `OpenAccount` to the search presenter**

Open `search/presenter.py`. Add a new method on the `Presenter` class, near `ExportData` / `ImportData`:

```python
    def OpenAccount(self):
        from account.client import AccountClient
        from account.dialogs import AccountDialog
        from account.tokenstore import TokenStore
        store = TokenStore()
        client = AccountClient(constants.ACCOUNT_BASE_URL, store)
        dlg = AccountDialog(self._view, client, store, self)
        dlg.ShowModal()
        dlg.Destroy()
```

- [ ] **Step 5: Smoke-import + run tests**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -c "import search.presenter, search.view, search.interactor, widgets; print('ok')"`
Expected: `ok` printed.

Run: `uv run --python /opt/homebrew/bin/python3.12 python test.py`
Expected: all tests still pass.

- [ ] **Step 6: Commit**

```bash
git add widgets/__init__.py search/view.py search/interactor.py search/presenter.py
git commit -m "feat(account): Account button on search toolbar opens AccountDialog"
```

---

## Task 7: Manual GUI verification

Not unit-testable; a human must drive the app.

- [ ] **Step 1: Launch**

Run: `uv run --python /opt/homebrew/bin/python3.12 python run.py`

- [ ] **Step 2: Sign up**

Open the Account dialog from the new toolbar button. Click "Sign up..." Enter a real email, a fresh username, and a password. Confirm "Verification email sent" appears. Click the link in the email to verify the account.

- [ ] **Step 3: Log in**

Reopen the Account dialog. Enter the verified username + password. Click Login. Confirm the dialog swaps to the logged-in view with "Signed in: <username>".

- [ ] **Step 4: Upload**

Click "Upload to Cloud". Confirm a success message and that the "Last upload" timestamp updates.

- [ ] **Step 5: Download**

Modify some local user data (add a bookmark or note). Click "Download latest". Confirm "Import complete" appears and that the previously-uploaded state replaces the modification.

- [ ] **Step 6: Manage backups**

Click "Manage backups...". Confirm the list shows the recent upload. Try Download on a row. Try Delete on an older row and confirm it disappears.

- [ ] **Step 7: Logout / re-login**

Click Logout. Confirm the dialog returns to the logged-out state. Re-login to confirm the token round-trips.

- [ ] **Step 8: Network failure**

Disconnect the network. Click "Upload to Cloud". Confirm the "Cannot reach server" message appears and the dialog recovers without crashing.

---

## Self-Review Notes

- **Spec coverage:**
  - Backend endpoints → `AccountClient` methods + tests (Task 3).
  - `.etz` format → `BuildBackupZip` (Task 4) + `_build_and_upload` (Task 5).
  - In-app sign-up → `SignUpDialog` (Task 5) calls `client.register`.
  - Manual sync semantics → explicit Upload/Download buttons (Task 5).
  - Single Account dialog → `AccountDialog` (Task 5); entry button Task 6.
  - Token store layout → Task 2.
  - Error handling (400/401/404/network) → `_show_error` Task 5.
  - Worker thread + `wx.CallAfter` → `_run_in_thread` Task 5.
  - Unit tests for client / tokenstore / export → Tasks 2, 3, 4 all register suites in `test.py`.
  - New constants + dep → Task 1.

- **Placeholder scan:** no TBD / TODO / "similar to". Every step has exact code or command.

- **Name consistency:**
  - `BuildBackupZip` exported from `search/presenter.py` (no leading underscore) so `account/dialogs.py` can import it.
  - `_run_in_thread`, `_show_error`, `_download_and_import`, `_build_and_upload`, `_download_latest` are module-private helpers in `account/dialogs.py`.
  - Public symbols: `TokenStore`, `AccountClient`, `AccountError`, `AccountDialog`, `SignUpDialog`, `BackupListDialog`.
  - All used names match across tasks.

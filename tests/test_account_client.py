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
    if json_body is not None and not content:
        content = json.dumps(json_body).encode('utf-8')
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
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

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


    @patch('account.client.requests.post')
    def testLogoutClearsLocalTokenOnSuccess(self, post):
        self.store.set('tok123', 'alice')
        post.return_value = _resp(200, {'detail': 'Successfully logged out.'})
        self.client.logout()
        self.assertFalse(self.store.is_logged_in())

    @patch('account.client.requests.post')
    def testLogoutClearsLocalTokenEvenOnServerError(self, post):
        self.store.set('tok123', 'alice')
        post.return_value = _resp(500, {'detail': 'boom'})
        with self.assertRaises(AccountError):
            self.client.logout()
        self.assertFalse(self.store.is_logged_in())

    @patch('account.client.requests.post')
    def testLogoutNoOpWhenNotLoggedIn(self, post):
        self.client.logout()
        post.assert_not_called()

    @patch('account.client.requests.post')
    def testLoginRaisesAccountErrorWhenKeyMissing(self, post):
        post.return_value = _resp(200, {'detail': 'no key here'})
        with self.assertRaises(AccountError) as cm:
            self.client.login('alice', 'pw')
        self.assertEqual(200, cm.exception.status)

    @patch('account.client.requests.post')
    def testLoginClearsStaleLastUploadBeforeStoringNewToken(self, post):
        self.store.set('older', 'bob')
        self.store.set_last_upload('2026-01-01T00:00:00')
        post.return_value = _resp(200, {'key': 'newtok'})
        self.client.login('alice', 'pw')
        data = self.store.get()
        self.assertEqual('newtok', data['token'])
        self.assertEqual('alice', data['username'])
        self.assertNotIn('last_upload', data)


def suite():
    s = unittest.TestSuite()
    for name in ['testLoginStoresToken', 'testLoginBadCredentialsRaises',
                 'testRegisterPostsFourFields', 'testLogoutPostsWithAuthHeader',
                 'testCurrentUser', 'testUploadPostsMultipart',
                 'testListBackupsParsesItemsJsonString',
                 'testDownloadReturnsBytes', 'testDeleteBackup',
                 'testUnauthorizedRaisesAccountError',
                 'testLogoutClearsLocalTokenOnSuccess',
                 'testLogoutClearsLocalTokenEvenOnServerError',
                 'testLogoutNoOpWhenNotLoggedIn',
                 'testLoginRaisesAccountErrorWhenKeyMissing',
                 'testLoginClearsStaleLastUploadBeforeStoringNewToken']:
        s.addTest(TestAccountClient(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

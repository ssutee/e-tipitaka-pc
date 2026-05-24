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
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

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


    def testCorruptedNonDictRootTreatedAsLoggedOut(self):
        with open(self.path, 'w') as f:
            f.write('[1, 2, 3]')
        self.assertIsNone(self.store.get())
        self.assertFalse(self.store.is_logged_in())
        # set() must still succeed (not raise TypeError).
        self.store.set('tok123', 'alice')
        self.assertEqual('tok123', self.store.get()['token'])


def suite():
    s = unittest.TestSuite()
    for name in ['testEmptyByDefault', 'testSetAndGetRoundTrip',
                 'testFilePersistsOnDisk', 'testClearRemovesData',
                 'testSetLastUploadPreservesToken',
                 'testMissingFileTreatedAsLoggedOut',
                 'testFileMode0600OnPosix',
                 'testCorruptedNonDictRootTreatedAsLoggedOut']:
        s.addTest(TestTokenStore(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

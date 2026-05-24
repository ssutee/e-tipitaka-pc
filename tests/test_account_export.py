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

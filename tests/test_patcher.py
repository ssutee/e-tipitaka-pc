#-*- coding:utf-8 -*-

import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from updates.patcher import (
    parse_index, compute_pending, PendingPatch, apply_chain,
    PatchError, get_local_version, ensure_user_copy,
)


SAMPLE_TOML = b'''
[thai]
version = 2
from.1 = "http://example.com/thai-1-2.sql"

[pali]
version = 3
from.2 = "http://example.com/pali-2-3.sql"
from.1 = "http://example.com/pali-1-2.sql"

[romanct]
version = 1
'''


class TestParseIndex(unittest.TestCase):

    def testParsesPlainTOML(self):
        idx = parse_index(SAMPLE_TOML)
        self.assertIn('thai', idx)
        self.assertEqual(2, idx['thai']['version'])
        self.assertEqual('http://example.com/thai-1-2.sql',
                         idx['thai']['from'][1])

    def testPaliHasTwoFromEntries(self):
        idx = parse_index(SAMPLE_TOML)
        self.assertEqual(3, idx['pali']['version'])
        self.assertEqual({1, 2}, set(idx['pali']['from']))

    def testEntryWithoutFromIsAllowed(self):
        idx = parse_index(SAMPLE_TOML)
        self.assertEqual(1, idx['romanct']['version'])
        self.assertEqual({}, idx['romanct']['from'])


class TestComputePending(unittest.TestCase):

    def setUp(self):
        self.idx = parse_index(SAMPLE_TOML)

    def testNoPatchWhenLocalAtTarget(self):
        pending = compute_pending(self.idx, local={'thai': 2, 'pali': 3})
        self.assertEqual([], pending)

    def testSingleStepUpgrade(self):
        pending = compute_pending(self.idx, local={'thai': 1, 'pali': 3})
        self.assertEqual(1, len(pending))
        p = pending[0]
        self.assertEqual('thai', p.db)
        self.assertEqual([(1, 2, 'http://example.com/thai-1-2.sql')], p.chain)

    def testMultiStepUpgradeAppliedInOrder(self):
        pending = compute_pending(self.idx, local={'thai': 2, 'pali': 1})
        # thai is at target, only pali should be pending
        self.assertEqual(['pali'], [p.db for p in pending])
        chain = pending[0].chain
        self.assertEqual([(1, 2, 'http://example.com/pali-1-2.sql'),
                          (2, 3, 'http://example.com/pali-2-3.sql')], chain)

    def testLocalZeroTreatedAsOne(self):
        # treat user_version=0 as 1 per project default
        pending = compute_pending(self.idx, local={'thai': 0})
        self.assertEqual(1, len(pending))
        self.assertEqual([(1, 2, 'http://example.com/thai-1-2.sql')],
                         pending[0].chain)

    def testShippedHigherThanRemoteSkippedSilently(self):
        # remote target is 2 for thai; local is at 5 → skip
        pending = compute_pending(self.idx, local={'thai': 5})
        self.assertEqual([], pending)

    def testMissingChainStepSkippedSilently(self):
        # remote claims target=3 but only has from.2; local at 1 → no path
        idx = parse_index(b'[pali]\nversion = 3\nfrom.2 = "http://x/p-2-3.sql"\n')
        pending = compute_pending(idx, local={'pali': 1})
        self.assertEqual([], pending)

    def testIgnoredDbNamesSkipped(self):
        idx = parse_index(b'[thaimc2]\nversion = 5\nfrom.1 = "http://x/thaimc2-1-2.sql"\n')
        pending = compute_pending(idx, local={'thaimc2': 1}, ignore=('thaimc2',))
        self.assertEqual([], pending)

    def testUnknownLocalDbSkipped(self):
        # remote lists a db we don't ship locally — ignored
        pending = compute_pending(self.idx, local={})
        self.assertEqual([], pending)


class TestGetLocalVersion(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, 'foo.sqlite')
        c = sqlite3.connect(self.path)
        c.executescript('PRAGMA user_version = 7;')
        c.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def testReadsUserVersion(self):
        self.assertEqual(7, get_local_version(self.path))


class TestEnsureUserCopy(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.shipped = os.path.join(self.tmp, 'shipped.sqlite')
        self.userdir = os.path.join(self.tmp, 'user')
        c = sqlite3.connect(self.shipped)
        c.executescript('CREATE TABLE t(x); INSERT INTO t VALUES (1);'
                        'PRAGMA user_version = 3;')
        c.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def testCopiesShippedToUserDirOnFirstCall(self):
        out = ensure_user_copy(self.shipped, self.userdir)
        self.assertEqual(os.path.join(self.userdir, 'shipped.sqlite'), out)
        self.assertTrue(os.path.exists(out))
        c = sqlite3.connect(out)
        self.assertEqual(3, c.execute('PRAGMA user_version').fetchone()[0])
        self.assertEqual(1, c.execute('SELECT x FROM t').fetchone()[0])
        c.close()

    def testSecondCallDoesNotOverwrite(self):
        out = ensure_user_copy(self.shipped, self.userdir)
        c = sqlite3.connect(out)
        c.executescript('UPDATE t SET x = 99; PRAGMA user_version = 4;')
        c.close()
        # second call: user copy already exists, must not be clobbered
        out2 = ensure_user_copy(self.shipped, self.userdir)
        self.assertEqual(out, out2)
        c = sqlite3.connect(out2)
        self.assertEqual(99, c.execute('SELECT x FROM t').fetchone()[0])
        self.assertEqual(4, c.execute('PRAGMA user_version').fetchone()[0])
        c.close()


def _make_patch_sql(from_ver, to_ver, table_update):
    return (
        'BEGIN;\n'
        'CREATE TEMP TABLE _vchk(x INTEGER);\n'
        'CREATE TEMP TRIGGER _vchk_t BEFORE INSERT ON _vchk\n'
        'BEGIN\n'
        '  SELECT CASE\n'
        '    WHEN (SELECT user_version FROM pragma_user_version()) != %d\n'
        "    THEN RAISE(ROLLBACK, 'wrong version') END;\n"
        'END;\n'
        'INSERT INTO _vchk VALUES (1);\n'
        'DROP TRIGGER _vchk_t;\n'
        'DROP TABLE _vchk;\n'
        '%s;\n'
        'PRAGMA user_version = %d;\n'
        'COMMIT;\n'
    ) % (from_ver, table_update, to_ver)


class TestApplyChain(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.shipped = os.path.join(self.tmp, 'foo.sqlite')
        self.userdir = os.path.join(self.tmp, 'user')
        c = sqlite3.connect(self.shipped)
        c.executescript('CREATE TABLE counter(n INTEGER); '
                        'INSERT INTO counter VALUES (0); '
                        'PRAGMA user_version = 1;')
        c.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_downloader(self, mapping):
        def _dl(url):
            return mapping[url].encode('utf-8')
        return _dl

    def testAppliesSingleStep(self):
        sql = _make_patch_sql(1, 2, "UPDATE counter SET n = 10")
        target = apply_chain(
            self.shipped, self.userdir,
            chain=[(1, 2, 'http://x/foo-1-2.sql')],
            downloader=self._make_downloader({'http://x/foo-1-2.sql': sql}),
        )
        c = sqlite3.connect(target)
        self.assertEqual(2, c.execute('PRAGMA user_version').fetchone()[0])
        self.assertEqual(10, c.execute('SELECT n FROM counter').fetchone()[0])
        c.close()
        # Shipped file untouched
        c = sqlite3.connect(self.shipped)
        self.assertEqual(1, c.execute('PRAGMA user_version').fetchone()[0])
        self.assertEqual(0, c.execute('SELECT n FROM counter').fetchone()[0])
        c.close()

    def testAppliesMultiStepInOrder(self):
        sql12 = _make_patch_sql(1, 2, "UPDATE counter SET n = 10")
        sql23 = _make_patch_sql(2, 3, "UPDATE counter SET n = 99")
        target = apply_chain(
            self.shipped, self.userdir,
            chain=[(1, 2, 'http://x/foo-1-2.sql'),
                   (2, 3, 'http://x/foo-2-3.sql')],
            downloader=self._make_downloader({
                'http://x/foo-1-2.sql': sql12,
                'http://x/foo-2-3.sql': sql23,
            }),
        )
        c = sqlite3.connect(target)
        self.assertEqual(3, c.execute('PRAGMA user_version').fetchone()[0])
        self.assertEqual(99, c.execute('SELECT n FROM counter').fetchone()[0])
        c.close()

    def testFailedPatchRollsBackAndRaises(self):
        bad = "BEGIN; SELECT not_a_real_function(); COMMIT;"
        with self.assertRaises(PatchError):
            apply_chain(
                self.shipped, self.userdir,
                chain=[(1, 2, 'http://x/bad.sql')],
                downloader=self._make_downloader({'http://x/bad.sql': bad}),
            )

    def testGuardAbortIfUserVersionWrong(self):
        # patch expects from=2 but user copy is at 1
        sql = _make_patch_sql(2, 3, "UPDATE counter SET n = 10")
        with self.assertRaises(PatchError):
            apply_chain(
                self.shipped, self.userdir,
                chain=[(2, 3, 'http://x/foo-2-3.sql')],
                downloader=self._make_downloader({'http://x/foo-2-3.sql': sql}),
            )


def suite():
    s = unittest.TestSuite()
    for cls in (TestParseIndex, TestComputePending, TestGetLocalVersion,
                TestEnsureUserCopy, TestApplyChain):
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            s.addTest(cls(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

#-*- coding:utf-8 -*-

import os
import sqlite3
import tempfile
import unittest

from search.presenter import (
    ImportSearchAndCompareHistory,
    ImportFavorites,
    ResolveIOSHighlightColor,
    AppendPCMark,
    DEFAULT_IOS_HIGHLIGHT_PALETTE,
)


SCH_SCHEMA = '''
CREATE TABLE "SearchAndCompareHistory" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "keywords1" TEXT NOT NULL,
  "keywords2" TEXT NOT NULL,
  "code1" TEXT NOT NULL,
  "code2" TEXT NOT NULL,
  "total" INTEGER NOT NULL,
  "count1" INTEGER,
  "count2" INTEGER
);
CREATE TABLE "SearchAndCompareHistoryReadItem" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "history" INTEGER REFERENCES "SearchAndCompareHistory" ("id") ON DELETE SET NULL,
  "row" INTEGER NOT NULL,
  "col" INTEGER NOT NULL
);
'''


FAV_TABLE_SCHEMA = (
    'CREATE TABLE %s (note TEXT, volume INTEGER, page INTEGER, parent_id INTEGER)'
)


def _mkdb(path, schema):
    c = sqlite3.connect(path)
    c.executescript(schema)
    c.commit()
    c.close()


def _exec(path, sql, params=()):
    c = sqlite3.connect(path)
    try:
        cur = c.executemany(sql, params) if isinstance(params, list) else c.execute(sql, params)
        c.commit()
    finally:
        c.close()


def _rows(path, sql):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


class TestImportSearchAndCompareHistory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, 'src.sqlite')
        self.dst = os.path.join(self.tmp, 'dst.sqlite')
        _mkdb(self.src, SCH_SCHEMA)
        _mkdb(self.dst, SCH_SCHEMA)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, path, sch_rows, item_rows):
        c = sqlite3.connect(path)
        c.executemany(
            'INSERT INTO SearchAndCompareHistory (id, keywords1, keywords2, code1, code2, total, count1, count2) VALUES (?,?,?,?,?,?,?,?)',
            sch_rows)
        c.executemany(
            'INSERT INTO SearchAndCompareHistoryReadItem (history, row, col) VALUES (?,?,?)',
            item_rows)
        c.commit()
        c.close()

    def testCopiesSchAndItemsIntoEmptyDest(self):
        self._seed(self.src,
                   [(1, 'k1', 'k2', 'c1', 'c2', 10, 4, 6),
                    (2, 'a1', 'a2', 'b1', 'b2', 5, 2, 3)],
                   [(1, 0, 0), (1, 1, 2), (2, 0, 0)])
        ImportSearchAndCompareHistory(self.src, self.dst)
        sch = _rows(self.dst, 'SELECT keywords1, keywords2, code1, code2, total, count1, count2 FROM SearchAndCompareHistory ORDER BY id')
        self.assertEqual([('k1', 'k2', 'c1', 'c2', 10, 4, 6),
                          ('a1', 'a2', 'b1', 'b2', 5, 2, 3)], sch)
        items = _rows(self.dst, 'SELECT history, row, col FROM SearchAndCompareHistoryReadItem ORDER BY id')
        # IDs are remapped, but counts must match
        self.assertEqual(3, len(items))

    def testDedupesByNaturalKey(self):
        # Dest already has the first row.
        self._seed(self.dst,
                   [(99, 'k1', 'k2', 'c1', 'c2', 10, 4, 6)],
                   [])
        self._seed(self.src,
                   [(1, 'k1', 'k2', 'c1', 'c2', 10, 4, 6),
                    (2, 'a1', 'a2', 'b1', 'b2', 5, 2, 3)],
                   [(1, 0, 0), (2, 0, 0)])
        ImportSearchAndCompareHistory(self.src, self.dst)
        sch = _rows(self.dst, 'SELECT keywords1, total FROM SearchAndCompareHistory ORDER BY id')
        self.assertEqual([('k1', 10), ('a1', 5)], sch)  # no duplicate of k1
        # Items: (src id 1 -> dst id 99), (src id 2 -> new dst id)
        items = _rows(self.dst, 'SELECT history, row, col FROM SearchAndCompareHistoryReadItem ORDER BY history')
        self.assertEqual(2, len(items))
        self.assertEqual(99, items[0][0])

    def testRunningTwiceIsIdempotent(self):
        self._seed(self.src,
                   [(1, 'k1', 'k2', 'c1', 'c2', 10, 4, 6)],
                   [(1, 0, 0), (1, 1, 1)])
        ImportSearchAndCompareHistory(self.src, self.dst)
        ImportSearchAndCompareHistory(self.src, self.dst)
        self.assertEqual(1, len(_rows(self.dst, 'SELECT * FROM SearchAndCompareHistory')))
        self.assertEqual(2, len(_rows(self.dst, 'SELECT * FROM SearchAndCompareHistoryReadItem')))

    def testOrphanedItemSkipped(self):
        # ReadItem references a history row that's missing in src
        self._seed(self.src, [], [(99, 0, 0)])
        ImportSearchAndCompareHistory(self.src, self.dst)
        self.assertEqual(0, len(_rows(self.dst, 'SELECT * FROM SearchAndCompareHistoryReadItem')))

    def testNoSchTablesInSrcDoesNotRaise(self):
        # src is empty (no SCH table at all). Function must tolerate.
        empty = os.path.join(self.tmp, 'empty.sqlite')
        sqlite3.connect(empty).close()
        ImportSearchAndCompareHistory(empty, self.dst)
        self.assertEqual(0, len(_rows(self.dst, 'SELECT * FROM SearchAndCompareHistory')))


class TestImportFavorites(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, 'fav-src.sqlite')
        self.dst = os.path.join(self.tmp, 'fav-dst.sqlite')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make(self, path, tables):
        """tables = {tablename: [(note, vol, page, parent_id), ...]}"""
        c = sqlite3.connect(path)
        for name in tables:
            c.execute(FAV_TABLE_SCHEMA % name)
        for name, rows in tables.items():
            c.executemany(
                'INSERT INTO "%s" (note, volume, page, parent_id) VALUES (?,?,?,?)' % name,
                rows)
        c.commit()
        c.close()

    def testCopiesAllTablesIntoEmptyDest(self):
        self._make(self.src, {
            'thai': [('n1', 1, 10, None), ('n2', 1, 11, 0)],
            'pali': [('p1', 2, 20, None)],
        })
        # dst has the tables but is empty
        self._make(self.dst, {'thai': [], 'pali': []})
        ImportFavorites(self.src, self.dst)
        self.assertEqual(2, len(_rows(self.dst, 'SELECT * FROM thai')))
        self.assertEqual(1, len(_rows(self.dst, 'SELECT * FROM pali')))

    def testCreatesMissingTablesInDest(self):
        # dst is completely empty — tables must be created from src schema
        self._make(self.src, {
            'thaiwn': [('w', 5, 50, None)],
            'palinew': [('pn', 6, 60, 1)],
        })
        sqlite3.connect(self.dst).close()
        ImportFavorites(self.src, self.dst)
        self.assertEqual(1, len(_rows(self.dst, 'SELECT * FROM thaiwn')))
        self.assertEqual(1, len(_rows(self.dst, 'SELECT * FROM palinew')))

    def testDedupesByAllFourColumns(self):
        self._make(self.src, {
            'thai': [('n1', 1, 10, None), ('n2', 1, 11, None)],
        })
        self._make(self.dst, {
            'thai': [('n1', 1, 10, None)],
        })
        ImportFavorites(self.src, self.dst)
        rows = _rows(self.dst, 'SELECT note, volume, page FROM thai ORDER BY page')
        self.assertEqual([('n1', 1, 10), ('n2', 1, 11)], rows)

    def testRunningTwiceIsIdempotent(self):
        self._make(self.src, {
            'thai': [('n1', 1, 10, None), ('n2', 1, 11, 0)],
        })
        self._make(self.dst, {'thai': []})
        ImportFavorites(self.src, self.dst)
        ImportFavorites(self.src, self.dst)
        self.assertEqual(2, len(_rows(self.dst, 'SELECT * FROM thai')))

    def testHandlesAllShippedFavTables(self):
        all_tables = ['thai', 'pali', 'thaiwn', 'thaimm', 'thaimc', 'thaipb',
                      'thaibt', 'romanct', 'palimc', 'thaims', 'thaivn',
                      'palinew', 'thaimc2']
        self._make(self.src, {t: [('n', 1, 1, None)] for t in all_tables})
        sqlite3.connect(self.dst).close()
        ImportFavorites(self.src, self.dst)
        for t in all_tables:
            self.assertEqual(1, len(_rows(self.dst, 'SELECT * FROM "%s"' % t)),
                             'table %s' % t)


class TestResolveIOSHighlightColor(unittest.TestCase):

    def testUsesFirstPaletteRowWhenAvailable(self):
        palette = [{'name': 'My', 'highlight1': '#AAAAAA', 'highlight2': '#BBBBBB'}]
        self.assertEqual('#AAAAAA', ResolveIOSHighlightColor(1, palette))
        self.assertEqual('#BBBBBB', ResolveIOSHighlightColor(2, palette))

    def testFallsBackToDefaultsWhenPaletteEmpty(self):
        self.assertEqual(DEFAULT_IOS_HIGHLIGHT_PALETTE[0],
                         ResolveIOSHighlightColor(1, []))
        self.assertEqual(DEFAULT_IOS_HIGHLIGHT_PALETTE[4],
                         ResolveIOSHighlightColor(5, []))

    def testFallsBackToDefaultsWhenPaletteEntryBlank(self):
        palette = [{'name': 'X', 'highlight1': ''}]
        self.assertEqual(DEFAULT_IOS_HIGHLIGHT_PALETTE[0],
                         ResolveIOSHighlightColor(1, palette))

    def testColorIndexZeroFallsBackToYellow(self):
        # iOS color=0 is the unset/default — pick a stable neutral.
        self.assertEqual('yellow', ResolveIOSHighlightColor(0, []))

    def testColorIndexOutOfRangeFallsBackToYellow(self):
        self.assertEqual('yellow', ResolveIOSHighlightColor(99, []))
        self.assertEqual('yellow', ResolveIOSHighlightColor(-1, []))


class TestAppendPCMark(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read(self, code, vol, page):
        import json as _json
        path = os.path.join(self.tmp, code, '%02d-%04d.json' % (vol, page))
        with open(path) as f:
            return _json.load(f)

    def testCreatesFileForFirstMark(self):
        AppendPCMark(self.tmp, 'thai', 1, 3, 13, 33, '#99FFFF')
        self.assertEqual([[True, 13, 33, '#99FFFF']],
                         self._read('thai', 1, 3))

    def testAppendsToExistingFile(self):
        AppendPCMark(self.tmp, 'thai', 1, 3, 13, 33, '#99FFFF')
        AppendPCMark(self.tmp, 'thai', 1, 3, 50, 70, 'yellow')
        self.assertEqual([[True, 13, 33, '#99FFFF'],
                          [True, 50, 70, 'yellow']],
                         self._read('thai', 1, 3))

    def testDedupesByStartAndEnd(self):
        AppendPCMark(self.tmp, 'thai', 1, 3, 13, 33, '#99FFFF')
        AppendPCMark(self.tmp, 'thai', 1, 3, 13, 33, 'yellow')   # same range, diff color
        self.assertEqual(1, len(self._read('thai', 1, 3)))

    def testCreatesNestedCodeDirectory(self):
        AppendPCMark(self.tmp, 'pali', 5, 100, 0, 10, 'yellow')
        path = os.path.join(self.tmp, 'pali', '05-0100.json')
        self.assertTrue(os.path.exists(path))


def suite():
    s = unittest.TestSuite()
    for cls in (TestImportSearchAndCompareHistory, TestImportFavorites,
                TestResolveIOSHighlightColor, TestAppendPCMark):
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            s.addTest(cls(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

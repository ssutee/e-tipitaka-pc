# -*- coding:utf-8 -*-

import unittest
import threads  # noqa: F401 – resolves utils/constants circular import
import utils
import read.view as rview
import read.presenter as rpresenter


class FakeView(object):
    """Bare stand-in carrying only the state the tested View methods touch."""
    def __init__(self):
        self._comparePanel = {}
        self.removed_panes = []
        self.destroyed = []

    def RemovePane(self, pane):
        self.removed_panes.append(pane)


class FakePanel(object):
    def __init__(self, view):
        self._view = view

    def Destroy(self):
        self._view.destroyed.append(self)


class TestNextCompareIndex(unittest.TestCase):
    """View._NextCompareIndex: exact-code match + max+1 (no reuse collisions)."""

    def _next(self, keys, code):
        view = FakeView()
        for k in keys:
            view._comparePanel[k] = object()
        return rview.View._NextCompareIndex(view, code)

    def testEmptyStartsAtOne(self):
        self.assertEqual(1, self._next([], 'pali'))

    def testIncrementsForSameCode(self):
        self.assertEqual(2, self._next(['pali:1'], 'pali'))

    def testExactCodeMatchOnly(self):
        # 'thai' must not be counted against 'thaimc' / 'thaiwn'.
        self.assertEqual(1, self._next(['thai:1', 'thai:2'], 'thaimc'))
        self.assertEqual(3, self._next(['thai:1', 'thai:2'], 'thai'))

    def testNoCollisionAfterClose(self):
        # Open pali:1, pali:2; close pali:1; reopening pali must NOT reuse 2.
        self.assertEqual(3, self._next(['pali:2'], 'pali'))


class TestRemoveReadPanel(unittest.TestCase):
    """View.RemoveReadPanel: pop from dict, detach pane, destroy widget."""

    def testRemovesDetachesDestroys(self):
        view = FakeView()
        panel = FakePanel(view)
        view._comparePanel[utils.MakeKey('pali', 1)] = panel

        rview.View.RemoveReadPanel(view, 'pali', 1)

        self.assertNotIn(utils.MakeKey('pali', 1), view._comparePanel)
        self.assertEqual([panel], view.removed_panes)
        self.assertEqual([panel], view.destroyed)

    def testMissingKeyIsNoOp(self):
        view = FakeView()
        rview.View.RemoveReadPanel(view, 'pali', 9)  # never opened
        self.assertEqual([], view.removed_panes)
        self.assertEqual([], view.destroyed)


class FakePresenterView(object):
    def __init__(self):
        self.removed = []

    def RemoveReadPanel(self, code, index):
        self.removed.append((code, index))


class FakePresenter(object):
    def __init__(self):
        self._view = FakePresenterView()
        self._compareVolume = {}
        self._comparePage = {}
        self._focusList = []
        self._lastFocus = None


class TestCloseComparePanel(unittest.TestCase):
    """Presenter.CloseComparePanel: tear down view pane + clean all state."""

    def _make(self, code, index, focus=False, last=False):
        p = FakePresenter()
        key = utils.MakeKey(code, index)
        p._compareVolume[key] = 5
        p._comparePage[key] = 12
        if focus:
            p._focusList.append(key)
        if last:
            p._lastFocus = key
        return p, key

    def testCleansCompareState(self):
        p, key = self._make('pali', 1)
        rpresenter.Presenter.CloseComparePanel(p, 'pali', 1)
        self.assertEqual([('pali', 1)], p._view.removed)
        self.assertNotIn(key, p._compareVolume)
        self.assertNotIn(key, p._comparePage)

    def testDropsFromFocusListAndLastFocus(self):
        p, key = self._make('pali', 2, focus=True, last=True)
        rpresenter.Presenter.CloseComparePanel(p, 'pali', 2)
        self.assertNotIn(key, p._focusList)
        self.assertIsNone(p._lastFocus)

    def testKeepsOtherPanelsLastFocus(self):
        p, key = self._make('pali', 1)
        other = utils.MakeKey('thai', 1)
        p._lastFocus = other
        rpresenter.Presenter.CloseComparePanel(p, 'pali', 1)
        self.assertEqual(other, p._lastFocus)  # untouched

    def testMainPanelIsNoOp(self):
        p = FakePresenter()
        rpresenter.Presenter.CloseComparePanel(p, None, 1)
        self.assertEqual([], p._view.removed)  # main panel never removed


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(TestNextCompareIndex),
        loader.loadTestsFromTestCase(TestRemoveReadPanel),
        loader.loadTestsFromTestCase(TestCloseComparePanel),
    ])


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

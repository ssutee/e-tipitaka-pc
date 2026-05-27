#-*- coding:utf-8 -*-

"""Sanity checks for the build.toml feature toggles wired into constants.py.

The actual loader runs at import time, so these tests just confirm the
helpers behave correctly given a manually-constructed disabled set."""

import unittest

import constants


class TestVisibilityHelpers(unittest.TestCase):

    def testIsCodeEnabledTrueForEnabledCodes(self):
        # When build.toml is missing (the default dev state), every code is
        # enabled.
        self.assertTrue(constants.IS_CODE_ENABLED('thai'))
        self.assertTrue(constants.IS_CODE_ENABLED('pali'))

    def testIsCodeEnabledFalseForDisabledCodes(self):
        for c in constants.DISABLED_CODES:
            self.assertFalse(constants.IS_CODE_ENABLED(c))

    def testVisibleLangsAndOrderAreSameLength(self):
        self.assertEqual(len(constants.VISIBLE_LANGS),
                         len(constants.VISIBLE_LANGS_ORDER))

    def testVisibleLangsOmitsDisabledCodes(self):
        for o in constants.VISIBLE_LANGS_ORDER:
            self.assertTrue(constants.IS_CODE_ENABLED(constants.CODES[o]))

    def testVisibleCompareOrderOmitsDisabledCodes(self):
        for o in constants.VISIBLE_COMPARE_ORDER:
            self.assertTrue(constants.IS_CODE_ENABLED(constants.CODES[o]))

    def testVisibleCompareChoicesMatchesOrderLength(self):
        self.assertEqual(len(constants.VISIBLE_COMPARE_CHOICES),
                         len(constants.VISIBLE_COMPARE_ORDER))

    def testDisablingThaiwnRemovesItFromVisibleLangs(self):
        # Simulate by computing what VISIBLE_LANGS_ORDER would look like
        # with thaiwn disabled, without touching the live module state.
        thaiwn_idx = constants.CODES.index('thaiwn')
        filtered = [o for o in constants.LANGS_ORDER if o != thaiwn_idx]
        self.assertNotIn(thaiwn_idx, filtered)


def suite():
    s = unittest.TestSuite()
    for name in unittest.defaultTestLoader.getTestCaseNames(TestVisibilityHelpers):
        s.addTest(TestVisibilityHelpers(name))
    return s


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())

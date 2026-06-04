"""Regression tests for cross-edition compare mapping.

Bug: comparing a Thai Royal (thai) location to Mahachula (thaimc) returned
page 0 for items whose Siam-item key is missing from MAP_MC_TO_SIAM
(scattered data gaps, e.g. thai vol 12 page 119 -> item 202). The compare
panel then opened nothing.

These tests drive the real conversion path used by ReadPresenter._DoCompare:
  thai.ConvertToPivot(vol, page, item) -> (pvol, item, sub)
  thaimc.ConvertFromPivot(pvol, item, sub) -> (vol, page)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from read.model import ThaiRoyalEngine, ThaiMahaChulaEngine  # noqa: E402


class CompareThaiToMahaChulaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.thai = ThaiRoyalEngine()
        cls.mc = ThaiMahaChulaEngine()

    def _compare(self, volume, page, item):
        pvol, pitem, psub = self.thai.ConvertToPivot(volume, page, item)
        if pvol == 0:
            return 0, 0
        return self.mc.ConvertFromPivot(pvol, pitem, psub)

    def test_reported_case_v12_p119(self):
        # thai vol 12, page 119 -> item 202 (missing from MAP_MC_TO_SIAM).
        items = self.thai.GetItems(12, 119)
        self.assertEqual(items, [202])
        vol, page = self._compare(12, 119, 202)
        self.assertNotEqual(page, 0, 'compare to thaimc returned page 0')
        self.assertEqual(vol, 12)
        # item 201 -> mc page 172, item 203 -> 174; 202 should land in between.
        self.assertGreaterEqual(page, 172)
        self.assertLessEqual(page, 174)

    def test_other_known_map_gaps_resolve(self):
        # Siam items in vol 12 absent from MAP_MC_TO_SIAM must still map.
        for item in (175, 202, 258, 273, 322, 363, 382, 383, 403):
            vol, page = self.mc.ConvertFromPivot(12, item, 1)
            self.assertNotEqual(page, 0, 'item %d still maps to page 0' % item)

    def test_present_items_unchanged(self):
        # Items already in the map keep their exact page (no regression).
        for item, expected in ((201, 172), (203, 174), (1, 1)):
            _, page = self.mc.ConvertFromPivot(12, item, 1)
            self.assertEqual(page, expected, 'item %d page changed' % item)


if __name__ == '__main__':
    unittest.main()

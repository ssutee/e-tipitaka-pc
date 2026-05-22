#-*- coding:utf-8 -*-

import unittest
import threads  # noqa: F401 – resolves utils/constants circular import
import wx
import utils


class TestApplyThemeRecursive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = wx.App()

    def setUp(self):
        self.frame = wx.Frame(None)
        self.bg = wx.Colour(0xF9, 0xEF, 0xD8, 0xFF)
        self.fg = wx.Colour(0x5E, 0x49, 0x33, 0xFF)

    def tearDown(self):
        self.frame.Destroy()

    def testRecolorsTopWindow(self):
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        self.assertEqual(self.bg, self.frame.GetBackgroundColour())
        self.assertEqual(self.fg, self.frame.GetForegroundColour())

    def testRecolorsNestedChildren(self):
        outer = wx.Panel(self.frame)
        inner = wx.Panel(outer)
        label = wx.StaticText(inner, label='x')
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        for w in (outer, inner, label):
            self.assertEqual(self.bg, w.GetBackgroundColour())
            self.assertEqual(self.fg, w.GetForegroundColour())

    def testRecolorsTextCtrlDefaultStyle(self):
        ctrl = wx.TextCtrl(self.frame, style=wx.TE_MULTILINE)
        ctrl.SetValue('some existing text')
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        attr = wx.TextAttr()
        ctrl.GetStyle(0, attr)  # mutates attr in-place
        # wx.Colour.__eq__ is broken for colours from TextAttr in wxPython 4.x;
        # compare via .Get() tuples instead.
        self.assertEqual(self.bg.Get(), attr.GetBackgroundColour().Get())
        self.assertEqual(self.fg.Get(), attr.GetTextColour().Get())

    def testRecolorsRichTextCtrl(self):
        ctrl = wx.richtext.RichTextCtrl(self.frame)
        ctrl.WriteText('note text')
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        attr = wx.TextAttr()
        ctrl.GetStyle(0, attr)  # mutates attr in-place
        # wx.Colour.__eq__ is broken for colours from TextAttr in wxPython 4.x;
        # compare via .Get() tuples instead.
        self.assertEqual(self.bg.Get(), attr.GetBackgroundColour().Get())
        self.assertEqual(self.fg.Get(), attr.GetTextColour().Get())


def suite():
    s = unittest.TestSuite()
    s.addTest(TestApplyThemeRecursive('testRecolorsTopWindow'))
    s.addTest(TestApplyThemeRecursive('testRecolorsNestedChildren'))
    s.addTest(TestApplyThemeRecursive('testRecolorsTextCtrlDefaultStyle'))
    s.addTest(TestApplyThemeRecursive('testRecolorsRichTextCtrl'))
    return s


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())

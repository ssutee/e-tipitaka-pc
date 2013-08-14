import wx
import os, sys, os.path
import widget
from wx.aui import AuiPaneInfo

import i18n
_ = i18n.language.ugettext

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PARENT_DIR)

from widget import AuiBaseFrame
import settings, constants

class View(AuiBaseFrame):
    def __init__(self):
        self.App = wx.App(redirect=False, clearSigInt=True, useBestVisual=True)
        super(View, self).__init__(None, id=wx.ID_ANY, size=(800, 600), title=self.AppName())

        icon = wx.IconBundle()
        icon.AddIconFromFile(constants.ICON_IMAGE, wx.BITMAP_TYPE_ANY)
        self.SetIcons(icon)

        self._language = 'thai'
        self._font = None
        
        self._resultsWindow = widget.ResultsWindow(self, self._language)
        self._topBar = widget.SearchToolPanel(self, self._font)
        
        self.SetCenterPane(self._resultsWindow)
        info = AuiPaneInfo().CloseButton(False).RightDockable(False).LeftDockable(False)
        info = info.FloatingSize((720, 125)).MinSize((720, 125)).Top()
        self.AddPane(self._topBar, info)
        
    def AppName(self):
        return '%s (%s)' % (_('AppName'), 'E-Tipitaka' + ' v' + settings.VERSION)  

    def Start(self):
        self.CenterOnScreen()
        self.Show()        
        self.App.MainLoop()

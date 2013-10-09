import wx
import os, sys, os.path
import widgets
from wx.aui import AuiPaneInfo

import i18n
_ = i18n.language.ugettext

from widgets import AuiBaseFrame
import settings, constants, utils
from dialogs import VolumesDialog

class View(AuiBaseFrame):
    
    @property
    def TopBar(self):
        return self._topBar
        
    @property
    def ForwardButton(self):
        return self._topBar.ForwardButton
        
    @property
    def BackwardButton(self):
        return self._topBar.BackwardButton
        
    @property
    def SearchCtrl(self):
        return self._topBar.SearchCtrl
    
    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        self.TopBar.Delegate = delegate
        self._resultsWindow.Delegate = delegate
        
    @property
    def ResultsWindow(self):
        return self._resultsWindow
        
    @property
    def StatusBar(self):
        return self._statusBar
        
    @property
    def VolumesRadio(self):
        return self._topBar.VolumesRadio
        
    @property
    def Font(self):
        return self._font
        
    @Font.setter
    def Font(self, font):
        self._font = font
        
    @property
    def HistoryList(self):
        return self._historyList

    def __init__(self):
        self.App = wx.App(redirect=False, clearSigInt=True, useBestVisual=True)
        super(View, self).__init__(None, id=wx.ID_ANY, size=(1024, 800), title=self.AppName())

        icon = wx.IconBundle()
        icon.AddIconFromFile(constants.ICON_IMAGE, wx.BITMAP_TYPE_ANY)
        self.SetIcons(icon)

        self._resultsWindow = widgets.ResultsWindow(self)
        
        self._font = utils.LoadFont(constants.SEARCH_FONT)
        if self._font and self._font.IsOk():
            self._resultsWindow.SetStandardFonts(self._font.GetPointSize(), self._font.GetFaceName())

        self._topBar = widgets.SearchToolPanel(self, self._font)
        self._CreateStatusBar()

        self.SetCenterPane(self._resultsWindow)
        info = AuiPaneInfo().CloseButton(False).Resizable(False).CaptionVisible(False)
        info = info.FloatingSize((720, 125)).MinSize((720, 125)).Top()
        self.AddPane(self._topBar, info)
        
        self._CreateHistoryListPane()

    def _CreateHistoryListPane(self):
        panel = wx.Panel(self, wx.ID_ANY)
        panel.SetBackgroundColour('white')
        sizer = wx.StaticBoxSizer(wx.StaticBox(panel, wx.ID_ANY, _('History')), orient=wx.VERTICAL)
        self._historyList = wx.ListBox(panel, wx.ID_ANY, choices=[], style=wx.LB_SINGLE|wx.LB_NEEDED_SB)
        sizer.Add(self._historyList, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        self.AddPane(panel, AuiPaneInfo().CloseButton(False).CaptionVisible(False).BestSize((200, -1)).Right())        

    def _CreateStatusBar(self):
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(4)
        self._statusBar.SetStatusWidths([-1,170,170,100])
        self._progressBar = wx.Gauge(self._statusBar, -1, 100, size=(100,-1))
        self._progressBar.SetBezelFace(3)
        self._progressBar.SetShadowWidth(3)
        self._progressBar.SetRect(self._statusBar.GetFieldRect(3))
        self._statusBar.Bind(wx.EVT_SIZE, lambda event: self._progressBar.SetRect(self._statusBar.GetFieldRect(3)))

    def DisableSearchControls(self):
        self._topBar.SearchButton.Disable()
        self._topBar.SearchButton.Refresh()
        self._topBar.ForwardButton.Disable()
        self._topBar.ForwardButton.Refresh()
        self._topBar.BackwardButton.Disable()
        self._topBar.BackwardButton.Refresh()      
        
    def EnableSearchControls(self):
        self._topBar.SearchButton.Enable()
        self._topBar.SearchButton.Refresh()
        self._topBar.ForwardButton.Enable()
        self._topBar.ForwardButton.Refresh()
        self._topBar.BackwardButton.Enable()
        self._topBar.BackwardButton.Refresh()   
        
    def SetPage(self, html):
        self._resultsWindow.SetPage(html)
        
    def SetProgress(self, progress):
        self._progressBar.SetValue(progress)
        
    def SetStatusText(self, text, position):
        self._statusBar.SetStatusText(text, position)
        
    def ScrollTo(self, position):
        self._resultsWindow.Scroll(0, position)
        self._resultsWindow.ScrollLines(position)
        
    def ShowVolumesDialog(self, dataSource, volumes, OnDismiss):
        dialog = VolumesDialog(self, volumes, dataSource)
        dialog.Center()        
        ret = dialog.ShowModal()
        OnDismiss(ret, dialog.GetCheckedVolumes())
        dialog.Destroy()
        
    def SetTitle(self, title):
        self.SetTitle(title)
        
    def SetHistoryListItems(self, items):
        self._historyList.SetItems(items)

    def AppName(self):
        return '%s (%s)' % (_('AppName'), 'E-Tipitaka' + ' v' + settings.VERSION)  

    def Start(self):
        self.CenterOnScreen()
        self.Show()        
        self.App.MainLoop()

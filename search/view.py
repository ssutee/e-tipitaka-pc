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
    def ExportButton(self):
        return self._topBar.ExportButton
        
    @property
    def ImportButton(self):
        return self._topBar.ImportButton
        
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
    def NikhahitButton(self):
        return self._topBar.NikhahitButton

    @property
    def ThothanButton(self):
        return self._topBar.ThothanButton

    @property
    def YoyingButton(self):
        return self._topBar.YoyingButton
                
    @property
    def Font(self):
        return self._font
        
    @Font.setter
    def Font(self, font):
        self._font = font
        
    @property
    def HistoryList(self):
        return self._historyList
        
    @property
    def SortingRadioBox(self):
        return self._sortingRadioBox
        
    @property
    def FilterCtrl(self):
        return self._filterCtrl
        
    @property
    def DeleteButton(self):
        return self._deleteButton

    def __init__(self):
        self.App = wx.App(redirect=False, clearSigInt=True, useBestVisual=True)
        super(View, self).__init__(None, id=wx.ID_ANY, title=self.AppName(),
            size=(min(1024, wx.DisplaySize()[0]), min(748, wx.DisplaySize()[1])))

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
        
        if 'wxMSW' in wx.PlatformInfo and self._font and self._font.IsOk():
            self._historyList.SetFont(self._font)
            
        self._sortingRadioBox = wx.RadioBox(panel, wx.ID_ANY, _('Sorting'), choices=[_('Alphabet'), _('Creation')], majorDimension=2)
        self._filterCtrl = wx.SearchCtrl(panel, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self._deleteButton = wx.BitmapButton(panel, wx.ID_ANY,
            wx.BitmapFromImage(wx.Image(constants.FILE_DELETE_IMAGE, wx.BITMAP_TYPE_PNG).Scale(18,18)))

        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)

        bottomSizer.Add(self._filterCtrl, 1, wx.ALIGN_CENTER)
        bottomSizer.Add((5,-1))        
        bottomSizer.Add(self._deleteButton, 0, wx.ALIGN_CENTER)
        
        sizer.Add(self._sortingRadioBox, 0, wx.ALIGN_CENTER|wx.BOTTOM, 5)
        sizer.Add(self._historyList, 1, wx.EXPAND|wx.BOTTOM, 2)
        sizer.Add(bottomSizer, 0, wx.EXPAND)
        
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
        for control in ['SearchButton', 'ForwardButton', 'BackwardButton']:
            getattr(self._topBar, control).Disable()
            getattr(self._topBar, control).Refresh()
        
    def EnableSearchControls(self):
        for control in ['SearchButton', 'ForwardButton', 'BackwardButton']:
            getattr(self._topBar, control).Enable()
            getattr(self._topBar, control).Refresh()
        
    def DisableHistoryControls(self):
        for control in ['_historyList', '_filterCtrl', '_sortingRadioBox', '_deleteButton']:
            getattr(self, control).Disable()
            getattr(self, control).Refresh()
        
    def EnableHistoryControls(self):
        for control in ['_historyList', '_filterCtrl', '_sortingRadioBox', '_deleteButton']:
            getattr(self, control).Enable()
            getattr(self, control).Refresh()
        
    def SetPage(self, html):
        self._resultsWindow.SetPage(html)
        
    def SetProgress(self, progress):
        self._progressBar.SetValue(progress)
        
    def SetStatusText(self, text, position):
        self._statusBar.SetStatusText(text, position)
        
    def ScrollTo(self, position):

        print position, self._resultsWindow.GetScrollPos(wx.HORIZONTAL)
        if 'wxMSW' in wx.PlatformInfo:
            self._resultsWindow.ScrollLines(position)
        else:
            self._resultsWindow.Scroll(0, position)
        
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

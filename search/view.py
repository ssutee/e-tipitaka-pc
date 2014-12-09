#-*- coding:utf-8 -*-

import wx
import os, sys, os.path
import widgets
from wx.aui import AuiPaneInfo

import i18n
_ = i18n.language.ugettext

from widgets import AuiBaseFrame
import settings, constants, utils
from dialogs import VolumesDialog, BookmarkManagerDialog

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
    def StarButton(self):
        return self._topBar.StarButton
        
    @property
    def NotesButton(self):
        return self._topBar.NotesButton
        
    @property
    def SearchCtrl(self):
        return self._topBar.SearchCtrl

    @property
    def BuddhawajOnly(self):
        return self._topBar._buddhawajOnly
    
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
    def PaliDictButton(self):
        return self._topBar.PaliDictButton
        
    @property
    def ThaiDictButton(self):
        return self._topBar.ThaiDictButton
                
    @property
    def ThemeComboBox(self):
        return self._topBar.ThemeComboBox
                
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
        
    def __init__(self, parent):        
        super(View, self).__init__(parent, -1, title=_('Search'), style=wx.CAPTION|wx.NO_BORDER)

        self._parent = parent
        self._bookmarkMenu = None

        self.SetBackgroundColour(wx.Colour(0xED,0xED,0xED,0xFF))
        
        self._resultsWindow = widgets.ResultsWindow(self)
        self._resultsWindow.SetPage(u'<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
        
        self._font = utils.LoadFont(constants.SEARCH_FONT)
        if self._font and self._font.IsOk():
            self._resultsWindow.SetStandardFonts(self._font.GetPointSize(), self._font.GetFaceName())
        
        self._topBar = widgets.SearchToolPanel(self, self._font)

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
        
        if 'wxMac' in wx.PlatformInfo:
            font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            font.SetFaceName('Tahoma')
            self._filterCtrl.SetFont(font)
        
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
        self._parent.ProgressBar.SetValue(progress)
        
    def SetStatusText(self, text, field):
        self._parent.StatusBar.SetStatusText(text, field)
        
    def ScrollTo(self, position):
        if 'wxMSW' in wx.PlatformInfo:
            self._resultsWindow.ScrollLines(position)
        else:
            self._resultsWindow.Scroll(0, position)
        
    def ShowBookmarkPopup(self, x, y):
        if self._bookmarkMenu is not None:
            self._bookmarkMenu.Destroy()
        self._bookmarkMenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnMenuManageBookmarkSelected, self._bookmarkMenu.Append(-1, u'จัดการคั่นหน้า'))        
        self._bookmarkMenu.AppendSeparator()                
        self._delegate.LoadBookmarks(self._bookmarkMenu)
        self._topBar.PopupMenu(self._bookmarkMenu, (x,y))        
    
    def GetBookmarkMenuItem(self, itemId):
        return self._bookmarkMenu.FindItemById(itemId)
                
    def OnMenuManageBookmarkSelected(self, event):
        dlg = BookmarkManagerDialog(self, self._delegate.BookmarkItems)
        dlg.ShowModal()
        self._delegate.SaveBookmark()
        dlg.Destroy()        
        
    def ShowVolumesDialog(self, dataSource, volumes, OnDismiss):
        dialog = VolumesDialog(self, volumes, dataSource)
        dialog.Center()        
        ret = dialog.ShowModal()
        OnDismiss(ret, dialog.GetCheckedVolumes())
        dialog.Destroy()
        
    def SetHistoryListItems(self, items):
        self._historyList.SetItems(items)    

    def Start(self):
        if wx.__version__[:3]<='2.8':
            self.Show()
        else:
            self.Activate()        

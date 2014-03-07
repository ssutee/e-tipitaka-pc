#-*- coding:utf-8 -*-

import wx
import os, sys, os.path
import widgets, constants, utils
from widgets import AuiBaseFrame
from dialogs import BookMarkDialog, BookmarkManagerDialog
from wx.aui import AuiPaneInfo

import i18n
_ = i18n.language.ugettext

class ReadPanelCreator(object):
    @staticmethod
    def Create(parent, code, font, delegate, mainWindow=False):
        if code == constants.THAI_FIVE_BOOKS_CODE:
            return widgets.ReadWithReferencesPanel(parent, code if not mainWindow else None, font, delegate)
        font = utils.LoadFont(constants.READ_FONT, code)
        return widgets.ReadPanel(parent, code if not mainWindow else None, font, delegate)

class ViewComponentsCreator(object):
    @staticmethod
    def Create(code, parent):
        if code == constants.THAI_FIVE_BOOKS_CODE:
            return ThaiFiveBooksViewComponents(parent)
        if code == constants.THAI_MAHACHULA_CODE:
            return ThaiMahaChulaViewComponents(parent)
        if code == constants.ROMAN_SCRIPT_CODE:
            return RomanScriptViewComponents(parent)
        if code == constants.THAI_SCRIPT_CODE:
            return ThaiScriptViewComponents(parent)
        return ViewComponents(parent)

class ViewComponents(object):
    
    def __init__(self, parent, dataSource=None):
        self._parent = parent
        self._dataSource = dataSource
    
    @property
    def DataSource(self):
        return self._dataSource
        
    @DataSource.setter
    def DataSource(self, dataSource):
        self._dataSource = dataSource
    
    def GetBookList(self, parent=None):
        bookList = wx.ListBox(parent if parent else self._parent, wx.ID_ANY, 
            choices=self._dataSource.GetBookListItems(), style=wx.LB_SINGLE|wx.NO_BORDER)
        bookList.SetSelection(0)
        return bookList
        
    def Filter(self, view):
        view.CheckBox.Hide()
        
class ThaiMahaChulaViewComponents(ViewComponents):
    
    def Filter(self, view):
        view.CheckBox.Show()
        
class ThaiFiveBooksViewComponents(ViewComponents):
    
    def GetBookList(self, parent=None):
        tree = wx.TreeCtrl(parent if parent else self._parent, wx.ID_ANY, 
            wx.DefaultPosition, wx.DefaultSize, style=wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS)
        self._InitTree(None, tree)
        return tree
        
    def _InitTree(self, data, tree):                
        root = tree.AddRoot('root')        
        keys = constants.FIVE_BOOKS_TOC.keys()
        keys.sort()
        for key in keys:
            volume = tree.AppendItem(root, constants.FIVE_BOOKS_NAMES[int(key)-1])
            tree.SetPyData(volume, tuple(constants.FIVE_BOOKS_TOC[key][0]) + (None,) )
            if int(key) == 1:
                self.FirstVolume = volume
            secs = map(int, constants.FIVE_BOOKS_TOC[key][1].keys())
            secs.sort()            
            for sec in secs:
                section = tree.AppendItem(volume, constants.FIVE_BOOKS_SECTIONS[int(key)][int(sec)])
                tree.SetPyData(section, tuple(constants.FIVE_BOOKS_TOC[key][1][str(sec)]) + (int(sec),))
        child, cookie = tree.GetFirstChild(root)
        tree.Expand(child)
    
    def Filter(self, view):
        view.CheckBox.Hide()
        view.InputItem.Disable()
        view.CompareComboBox.Disable()
        
class ScriptViewComponents(ViewComponents):
    
    def GetBookList(self, parent=None):
        tree = wx.TreeCtrl(parent if parent else self._parent, wx.ID_ANY, 
            wx.DefaultPosition, wx.DefaultSize, style=wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS)
        self._InitTree(None, tree)
        return tree
        
    def _InitTree(self, data, tree):

        def _traverse(toc, tree, root):
            for node in toc['items']:
                leaf = tree.AppendItem(root, node['name'])
                tree.SetPyData(leaf, node['info']+[0])
                _traverse(node, tree, leaf)

        root_tree = tree.AddRoot('root')
        root_toc = self._toc
        _traverse(root_toc, tree, root_tree)
        child, cookie = tree.GetFirstChild(root_tree)
        tree.Expand(child)
                
    def Filter(self, view):
        view.CheckBox.Hide()
        view.CompareComboBox.Disable()
        
class ThaiScriptViewComponents(ScriptViewComponents):
    
    def __init__(self, parent, dataSource=None):
        super(ThaiScriptViewComponents, self).__init__(parent, dataSource)
        self._toc = constants.THAI_SCRIPT_TOC
        
class RomanScriptViewComponents(ScriptViewComponents):
    def __init__(self, parent, dataSource=None):
        super(RomanScriptViewComponents, self).__init__(parent, dataSource)
        self._toc = constants.ROMAN_SCRIPT_TOC
        
class View(AuiBaseFrame):    
    
    def __init__(self, parent, title, code):         
        rect = utils.LoadReadWindowPosition()
        
        pos = 0,0
        if rect is not None:
            pos = rect[0], rect[1]

        size = min(1024, wx.DisplaySize()[0]), min(748, wx.DisplaySize()[1])
        if rect is not None:
            size = rect[2], rect[3]
                
        super(View, self).__init__(parent, wx.ID_ANY, title=title, size=size, pos=pos)
            
        if rect is None:
            self.CenterOnScreen()            
            
        self._dataSource = None
        self._delegate = None
        
        self._components = ViewComponentsCreator.Create(code, self)
        self._code = code                
        self._readPanel = None
        self._comparePanel = {}
        
        self._font = utils.LoadFont(constants.READ_FONT, code)
        
        self._bookmarkMenu = None
        self._SetupStatusBar()
        
    @property
    def Font(self):
        return self._font
        
    @Font.setter
    def Font(self, font):
        self._font = font
            
    def SetFont(self, font, code):
        self._readPanel.SetContentFont(font) if code is None else self._comparePanel[code].SetContentFont(font)

    @property
    def DataSource(self):
        return self._dataSource

    @DataSource.setter
    def DataSource(self, dataSource):
        self._dataSource = dataSource
        self._components.DataSource = dataSource        
        
    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    @property
    def ForwardButton(self):
        return self._toolPanel.ForwardButton
    
    @property
    def BackwardButton(self):
        return self._toolPanel.BackwardButton
        
    @property
    def FontsButton(self):
        return self._toolPanel.FontsButton
        
    @property
    def IncreaseFontButton(self):
        return self._toolPanel.IncreaseFontButton
        
    @property
    def DecreaseFontButton(self):
        return self._toolPanel.DecreaseFontButton
        
    @property
    def BookListButton(self):
        return self._toolPanel.BookListButton
        
    @property
    def StarButton(self):
        return self._toolPanel.StarButton
        
    @property
    def SearchButton(self):
        return self._toolPanel.SearchButton
        
    @property
    def PrintButton(self):
        return self._toolPanel.PrintButton
        
    @property
    def SaveButton(self):
        return self._toolPanel.SaveButton

    @property
    def DictButton(self):
        return self._toolPanel.DictButton
        
    @property
    def NotesButton(self):
        return self._toolPanel.NotesButton

    @property
    def InputItem(self):
        return self._inputItem
        
    @property
    def CheckBox(self):
        return self._checkBox
        
    @property
    def CompareComboBox(self):
        return self._toolPanel.CompareComboBox

    @property
    def BookList(self):
        return self._bookList
        
    @property
    def InputPage(self):
        return self._inputPage
        
    @property
    def InputItem(self):
        return self._inputItem
        
    @property
    def CheckBox(self):
        return self._checkBox

    @property
    def Body(self):
        return self._readPanel.Body
        
    @property
    def NotePanel(self):
        return self._notePanel
        
    @property
    def NoteTextCtrl(self):
        return self._notePanel.NoteTextCtrl
        
    @property
    def StatusBar(self):
        return self._statusBar

    def _SetupStatusBar(self):
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(2)
        self._statusBar.SetStatusWidths([-1,-1])
        font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        font.SetFaceName('TF Chiangsaen')
        self._statusBar.SetFont(font)                

    def _PostInit(self):            
        self._readPanel = ReadPanelCreator.Create(self, self._code, self._font, self._delegate, mainWindow=True)
        self._readPanel.Delegate = self._delegate
        self._readPanel.SetPageNumber(None)
        self._readPanel.SetItemNumber(None)

        self._toolPanel = widgets.ReadToolPanel(self, self._dataSource)        
        self._listPanel = self._CreateBookListPanel()        
        
        self.SetCenterPane(self._readPanel, caption=True)

        info = AuiPaneInfo().CaptionVisible(False).Resizable(False)
        info = info.FloatingSize((740, 65)).MinSize((740, 65)).Top().Layer(0)
        self.AddPane(self._toolPanel, info.Name('Tool'))

        self._notePanel = widgets.NotePanel(self)
        info = AuiPaneInfo().CaptionVisible(False).Resizable(True).BestSize((740, 110)).Bottom()        
        self.AddPane(self._notePanel, info.Name('Note'))

        info = AuiPaneInfo().CaptionVisible(False).TopDockable(False).BottomDockable(False)
        info = info.BestSize((250, 768)).FloatingSize((250, 768)).MinSize((0, 0)).Left().Layer(1)        
        self.AddPane(self._listPanel, info.Name('BookList'))        
        
    def _CreateBookListPanel(self):
        panel = wx.Panel(self, wx.ID_ANY)        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._bookList = self._components.GetBookList(panel)
        
        naviPanel = wx.Panel(panel, wx.ID_ANY)
        naviSizer = wx.StaticBoxSizer(wx.StaticBox(naviPanel, wx.ID_ANY, u'เลือกอ่านที่'), orient=wx.HORIZONTAL)

        labelPage = wx.StaticText(naviPanel, wx.ID_ANY, u'หน้า: ')
        labelItem = wx.StaticText(naviPanel, wx.ID_ANY, u'ข้อ: ')
        
        self._inputPage = wx.TextCtrl(naviPanel, wx.ID_ANY, size=(50,-1), style=wx.TE_PROCESS_ENTER)
		
        self._inputItem = wx.TextCtrl(naviPanel, wx.ID_ANY, size=(50,-1), style=wx.TE_PROCESS_ENTER)
        
        self._checkBox = wx.CheckBox(naviPanel, wx.ID_ANY, label=u'=สยามรัฐฯ')
		
        naviSizer.Add(labelPage, flag=wx.ALIGN_CENTER_VERTICAL)
        naviSizer.Add(self._inputPage, flag=wx.ALIGN_CENTER_VERTICAL)
        naviSizer.Add(wx.StaticText(panel, wx.ID_ANY, u'  หรือ  '), flag=wx.ALIGN_CENTER_VERTICAL)
        naviSizer.Add(labelItem, flag=wx.ALIGN_CENTER_VERTICAL)
        naviSizer.Add(self._inputItem, flag=wx.ALIGN_CENTER_VERTICAL)
        naviSizer.Add((5,-1))
        naviSizer.Add(self._checkBox,flag=wx.ALIGN_CENTER_VERTICAL)
        
        naviPanel.SetSizer(naviSizer)
        
        sizer.Add(naviPanel, 0, wx.EXPAND)
        sizer.Add(self._bookList, 1, wx.EXPAND)
        
        panel.SetSizer(sizer)
        
        return panel        
        
    def AddReadPanel(self, code):
        if code not in self._comparePanel:
            self._comparePanel[code] = ReadPanelCreator.Create(self, code, self._font, self._delegate)
            info = AuiPaneInfo().Floatable(False).Center().Row(len(self._comparePanel))
            self.AddPane(self._comparePanel[code], info.Name(code))
        else:
            info = self.AuiManager.GetPane(self._comparePanel[code])
            info.Show()
            self.AuiManager.Update()
            
    def HideBookList(self):
        info = self.AuiManager.GetPane('BookList')
        info.Hide()
        self.AuiManager.Update()

    def ShowBookList(self):
        info = self.AuiManager.GetPane('Note')
        info.Show()        
        self.AuiManager.Update()

    def HideNote(self):
        info = self.AuiManager.GetPane('Note')
        info.Hide()        
        self.AuiManager.Update()

    def ShowNote(self):
        info = self.AuiManager.GetPane('Note')
        info.Show()        
        self.AuiManager.Update()

    def ToggleBookList(self):
        info = self.AuiManager.GetPane('BookList')
        flag = info.IsShown()
        info.Hide() if flag else info.Show()   
        info = self.AuiManager.GetPane('Note')
        info.Hide() if flag else info.Show()   
        self.AuiManager.Update()

    def SetPageNumber(self, number, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.SetPageNumber(number)
        
    def SetItemNumber(self, *numbers, **kwargs):
        readPanel = self._readPanel if 'code' not in kwargs else self._comparePanel[kwargs['code']]
        readPanel.SetItemNumber(*numbers)
        
    def SetTitles(self, title1, title2, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.SetTitles(title1, title2)
        
    def SetText(self, text, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.SetBody(text)
        
    def GetStringSelection(self, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        return readPanel.Body.GetStringSelection()
        
    def MarkText(self, code, selection=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        s,t = readPanel.Body.GetSelection() if selection is None else selection
        font = readPanel.Body.GetFont()

        if 'wxMac' in wx.PlatformInfo:
            readPanel.Body.SetStyle(s, t, wx.TextAttr('blue', wx.NullColour, 
                wx.Font(font.GetPointSize()+2, font.GetFamily(), font.GetStyle(), wx.FONTWEIGHT_BOLD, False, font.GetFaceName())))
        else:
            readPanel.Body.SetStyle(s, t, wx.TextAttr(wx.NullColour, 'yellow', font))
            
        return s,t
            
    def UnmarkText(self, code, selection=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        s,t = readPanel.Body.GetSelection() if selection is None else selection
        font = readPanel.Body.GetFont()
        readPanel.Body.SetStyle(s, t, wx.TextAttr(wx.NullColour, 'white', font))    

        return s,t
        
    def ClearMarks(self, code):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        font = readPanel.Body.GetFont()
        text = readPanel.Body.GetValue()
        readPanel.Body.SetFont(font)   
        readPanel.Body.SetStyle(0, len(text)+1, wx.TextAttr(wx.NullColour, 'white', font))    
                
    def FormatText(self, formatter, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        font = readPanel.Body.GetFont()
        fontSize = font.GetPointSize()
        readPanel.Body.Freeze()
        if 'wxMac' in wx.PlatformInfo:
            readPanel.SetContentFont(font)
        
        for token in formatter.split():
            tag,x,y = token.split('|')
            if tag == 's3' or tag == 'p3':
                colorCode, diffSize = constants.FOOTER_STYLE
                font.SetPointSize(fontSize-diffSize)
                if 'wxMac' not in wx.PlatformInfo:
                    readPanel.Body.SetStyle(int(x), int(y), wx.TextAttr(colorCode, wx.NullColour, font))
                else:
                    readPanel.Body.SetStyle(int(x)-1, int(y)-1, wx.TextAttr(colorCode, wx.NullColour, font))
            elif tag == 'h1' or tag == 'h2' or tag == 'h3':
                font.SetPointSize(fontSize)
                if 'wxMac' not in wx.PlatformInfo:
                    readPanel.Body.SetStyle(int(x), int(y), wx.TextAttr('blue', wx.NullColour, font))
                else:
                    readPanel.Body.SetStyle(int(x)-1, int(y)-1, wx.TextAttr('blue', wx.NullColour, font))  
        readPanel.Body.Thaw()     
        
    def ShowFindDialog(self, code, text, flags):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        data = wx.FindReplaceData()
        data.SetFlags(flags)
        data.SetFindString(text)
        dlg = wx.FindReplaceDialog(readPanel, data, "Find", style=wx.FR_NOMATCHCASE|wx.FR_NOWHOLEWORD)
        dlg.data = data
        dlg.Show(True)
        
    def ShowBookmarkPopup(self, x, y):
        if self._bookmarkMenu is not None:
            self._bookmarkMenu.Destroy()
        self._bookmarkMenu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnMenuAddBookmarkSelected, self._bookmarkMenu.Append(-1, u'คั่นหน้านี้'))
        self.Bind(wx.EVT_MENU, self.OnMenuManageBookmarkSelected, self._bookmarkMenu.Append(-1, u'จัดการคั่นหน้า'))        
        self._bookmarkMenu.AppendSeparator()        
        self._delegate.LoadBookmarks(self._bookmarkMenu)
        self._toolPanel.PopupMenu(self._bookmarkMenu, (x,y))
        
    def ShowContextMenu(self, window, position, code):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        
        def OnCopy(event):
            if isinstance(window, wx.html.HtmlWindow):
                clipdata = wx.TextDataObject()
                clipdata.SetText(window.SelectionToText())
                wx.TheClipboard.Open()
                wx.TheClipboard.SetData(clipdata)
                wx.TheClipboard.Close()
            elif isinstance(window, wx.TextCtrl):
                window.Copy()
            
        def OnSelectAll(event):
            window.SelectAll()
            
        def OnSearch(event):
            text = u''
            if isinstance(window, wx.html.HtmlWindow):
                text = window.SelectionToText()
            elif isinstance(window, wx.TextCtrl):
                text = window.GetStringSelection()
            self._delegate.SearchSelection(text)
                    
        menu = wx.Menu()
        search = menu.Append(constants.ID_SEARCH, u'ค้นหา')
        menu.AppendSeparator()
        copy = menu.Append(constants.ID_COPY, u'คัดลอก')
        if isinstance(window, wx.TextCtrl):
            copy.Enable(window.CanCopy())
        elif isinstance(window, wx.html.HtmlWindow):
            copy.Enable(len(window.SelectionToText()) > 0)
        selectAll = menu.Append(constants.ID_SELECT_ALL, u'เลือกทั้งหมด')
        wx.EVT_MENU(menu, constants.ID_COPY, OnCopy)
        wx.EVT_MENU(menu, constants.ID_SELECT_ALL, OnSelectAll)
        wx.EVT_MENU(menu, constants.ID_SEARCH, OnSearch)
        window.PopupMenu(menu, position)                        
        menu.Destroy()        
        
    def GetBookmarkMenuItem(self, itemId):
        return self._bookmarkMenu.FindItemById(itemId)
        
    def OnMenuAddBookmarkSelected(self, event):
        volume, page = self._delegate.CurrentVolume, self._delegate.CurrentPage
        if page != 0:
            x,y = self.StarButton.GetScreenPosition()
            w,h = self.StarButton.GetSize()        
            dialog = BookMarkDialog(self._readPanel, self._delegate.BookmarkItems)
            if dialog.ShowModal() == wx.ID_OK:
                result = dialog.GetValue()
                if result != None and len(result) == 2:
                    container, note = result
                    note = u'%s : %s' %(utils.ArabicToThai(u'เล่มที่ %d หน้าที่ %d'%(volume, page)), note)
                    container.append((volume, page, note))
            dialog.Destroy()
        else:
            wx.MessageBox(u'หน้ายังไม่ได้ถูกเลือก',u'พบข้อผิดพลาด')
        
    def SetBookListSelection(self, volume):
        if isinstance(self._bookList, wx.ListBox):
            self._bookList.SetSelection(volume-1)
        
    def OnMenuManageBookmarkSelected(self, event):
        dlg = BookmarkManagerDialog(self._readPanel, self._delegate.BookmarkItems)
        dlg.ShowModal()
        dlg.Destroy()
        
    def SetSelection(self, content, start, end, code):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.Body.SetSelection(start, end)
                
    def UpdateSlider(self, value, minimum, maximum, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.Slider.SetMin(minimum)
        readPanel.Slider.SetMax(maximum)
        readPanel.Slider.SetValue(value)
        
    def Start(self):
        self._PostInit()
        self._components.Filter(self)
        self.Show()        

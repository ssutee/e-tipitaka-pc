#-*- coding:utf-8 -*-

import wx

try:
    import wx.aui as aui
except ImportError,e:
    import wx.lib.agw.aui as aui

import wx.lib.buttons as buttons
import wx.html
import sys, os, os.path, sys, codecs, re, cPickle, sqlite3
import wx.richtext as rt
import wx.lib.buttons as buttons
import wx.grid

from wx.lib.splitter import MultiSplitterWindow
import constants, utils
import i18n, images
import abc

import search.model
import read.model

import random

_ = i18n.language.ugettext


class CustomTableGrid(wx.grid.Grid):
    def __init__(self, parent, dataSource, delegate):
        wx.grid.Grid.__init__(self, parent,wx.ID_ANY)

        self._dataSource = None
        self._delegate = delegate

        table = CustomDataTable(dataSource)
        self.SetTable(table, True)

        self.SetRowLabelSize(0)
        self.SetMargins(0,0)
        self.AutoSizeColumns(False)

        wx.grid.EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick)

    def OnLeftDClick(self, evt):
        self._delegate.OnLeftDClick(evt.Col, evt.Row)


class CustomDataTable(wx.grid.PyGridTableBase):
    def __init__(self, dataSource):
        wx.grid.PyGridTableBase.__init__(self)
        self.dataSource = dataSource

    def GetNumberRows(self):
        return self.dataSource.GetNumberRows()

    def GetNumberCols(self):
        return self.dataSource.GetNumberCols()

    def IsEmptyCell(self, row, col):
        try:
            return not self.dataSource.GetData(row, col)
        except IndexError:
            return True

    def GetValue(self, row, col):
        try:
            return self.dataSource.GetData(row, col)
        except IndexError:
            return ''

    def GetColLabelValue(self, col):
        return self.dataSource.GetColLabelValue(col)

    def GetTypeName(self, row, col):
        return self.dataSource.GetTypeName(row, col)


class SearchAndCompareWindow(wx.Frame):
    # CustomDataTable data source
    def GetNumberRows(self):
        return len(self.matchItems)

    def GetNumberCols(self):
        return 2

    def GetData(self, row, col):
        volume1, page1, item1, volume2, page2, item2 = self.matchItems[row]
        if col == 0:
            return utils.ArabicToThai(u'เล่มที่ %d หน้าที่ %d ข้อที่ %d' % (volume1, page1, item1))
        if col == 1:
            return utils.ArabicToThai(u'เล่มที่ %d หน้าที่ %d ข้อที่ %d' % (volume2, page2, item2))
        return ''

    def GetTypeName(self, row, col) :
        return wx.grid.GRID_VALUE_STRING

    def GetColLabelValue(self, col):
        if col == 0:
            return self.combo1.GetStringSelection()
        if col == 1:
            return self.combo2.GetStringSelection()
        return u''

    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, value):
        self._delegate = value

    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self._delegate = None

        self.matchItems = []

        mainPanel = wx.Panel(self,-1,style=wx.TAB_TRAVERSAL,size=(800,600))

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.SetBackgroundColour('#EEEEEE')

        icon = wx.IconBundle()
        icon.AddIconFromFile(constants.SEARCH_AND_COMPARE_ICON, wx.BITMAP_TYPE_ANY)
        self.SetIcons(icon)

        self.SetWindowStyle( self.GetWindowStyle() | wx.STAY_ON_TOP) 

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.combo1 = wx.ComboBox(mainPanel, wx.ID_ANY, choices=constants.LANGS, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.combo2 = wx.ComboBox(mainPanel, wx.ID_ANY, choices=constants.LANGS, style=wx.CB_DROPDOWN|wx.CB_READONLY)

        self.ctrl1 = wx.TextCtrl(mainPanel, wx.ID_ANY)
        self.ctrl2 = wx.TextCtrl(mainPanel, wx.ID_ANY)

        self.searchButton = wx.Button(mainPanel, wx.ID_ANY, _('Search'), size=(80,-1))
        self.searchButton.Bind(wx.EVT_BUTTON, self.OnSearchButtonClick)

        sizer1.Add(self.combo1, 0)
        sizer1.Add(self.ctrl1, 1, wx.LEFT|wx.RIGHT, 5)
        sizer1.Add((80, 0), 0)

        sizer2.Add(self.combo2,0)
        sizer2.Add(self.ctrl2, 1, wx.LEFT|wx.RIGHT, 5)
        sizer2.Add(self.searchButton, 0)

        mainSizer.Add(sizer1, 0, wx.EXPAND|wx.ALL, 5)
        mainSizer.Add(sizer2, 0, wx.EXPAND|wx.ALL, 5)

        self.grid = CustomTableGrid(mainPanel, self, self)
        self.grid.EnableEditing(False)
        self.grid.SetDefaultColSize(395)

        mainSizer.Add(self.grid, 1, wx.EXPAND|wx.ALL, 5)

        mainPanel.SetSizer(mainSizer)

        sizer.Add(mainPanel, 1, wx.EXPAND)

        self.SetSizer(sizer)

        self.SetSize((800,600))
        self.Center()        

        self.model1 = None
        self.model2 = None

        self.readModel1 = None
        self.readModel2 = None

        self.results1 = None
        self.results2 = None


    def ReloadTable(self):
        table = CustomDataTable(self)
        self.grid.SetTable(table, True)
        self.grid.ForceRefresh()
        self.grid.Update()

    def OnSearchButtonClick(self, event):
        self.results1 = None
        self.results2 = None

        index1 = self.combo1.GetSelection()
        index2 = self.combo2.GetSelection()
        self.text1 = self.ctrl1.GetValue().strip()
        self.text2 = self.ctrl2.GetValue().strip()

        if index1 != -1 and index2 != -1 and len(self.text1) > 0 and len(self.text2) > 0:
            self.model1 = search.model.SearchModelCreator.Create(self, index1)
            self.model2 = search.model.SearchModelCreator.Create(self, index2)
            self.model1.Search(self.text1)

    def OnLeftDClick(self, col, row):
        volume1, page1, item1, volume2, page2, item2 = self.matchItems[row]
        if col == 0:
            self._delegate.OnSearchAndCompareItemClick(self.model1.Code, volume1, page1, self.text1)
        if col == 1:
            self._delegate.OnSearchAndCompareItemClick(self.model2.Code, volume2, page2, self.text2)

    def SearchWillStart(self, keywords):
        self.searchButton.Enable(False)

    def SearchDidFinish(self, results, keywords):
        self.searchButton.Enable(True)
        if self.results1 is None:
            self.results1 = results
            self.MatchItems()

    def MatchItems(self):
        self.matchItems = []

        if len(self.results1) == 0:
            return

        self.readModel1 = read.model.Model(self.model1.Code)
        self.readModel2 = read.model.Model(self.model2.Code)

        for r1 in self.results1:
            volume = int(r1['volume'])
            page = int(r1['page'])
            items1 = self.readModel1.GetItems(volume, page)
            for item1 in items1:
                result = self._DoCompare(volume, page, item1)
            
                if result is None:
                    continue
                
                volume2, page2, item2 = result
                content = self.readModel2.GetPage(volume2, page2)
                
                matchKey = (volume, page, item1, volume2, page2, item2)
                if content.find(self.text2) > -1 and matchKey not in self.matchItems:
                    self.matchItems.append(matchKey)
        
        self.ReloadTable()  

    def _DoCompare(self, volume, page, item):        
        if item is None: return
        
        volume, item, sub = self.readModel1.ConvertToPivot(volume, page, item)
        
        if volume == 0:
            return

        volume, page = self.readModel2.ConvertFromPivot(volume, item, sub)

        if volume == 0:
            return

        return volume, page, item        

class DictWindow(wx.Frame):
    
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.SetBackgroundColour('#EEEEEE')
        icon = wx.IconBundle()
        icon.AddIconFromFile(constants.DICT_ICON, wx.BITMAP_TYPE_ANY)
        self.SetIcons(icon)

        self.SetWindowStyle( self.GetWindowStyle() | wx.STAY_ON_TOP ) 
        
        self.SetSize((705,400))
        self.Center()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.hboxToolbar = wx.BoxSizer(wx.HORIZONTAL)

        labelWord = wx.StaticText(self, -1, u'ค้นหา: ')
        self.input = wx.SearchCtrl(self, -1, pos=(0,0), size=(-1,-1), style=wx.TE_PROCESS_ENTER)

        self.input.Bind(wx.EVT_TEXT_ENTER, self.OnTextEntered)
        self.input.Bind(wx.EVT_TEXT, self.OnTextEntered)

        self.hboxToolbar.Add(labelWord, 0, wx.ALL | wx.CENTER | wx.ALIGN_RIGHT, 5)
        self.hboxToolbar.Add(self.input, 1, wx.ALL | wx.CENTER, 1)
        
        mainSizer.Add(self.hboxToolbar,0,wx.EXPAND | wx.ALL)

        self.SetupAdditionalToolbar(mainSizer)

        self.sp = wx.SplitterWindow(self,-1)
        mainSizer.Add(self.sp,1,wx.EXPAND)
        
        self.rightPanel = wx.Panel(self.sp,-1)
        self.text = wx.TextCtrl(self.rightPanel, -1, style=wx.NO_BORDER|wx.TE_MULTILINE|wx.TE_RICH2)

        font, fontError = self.SetupFont()

        rightSizer = wx.StaticBoxSizer(wx.StaticBox(self.rightPanel, -1, u'คำแปล'), wx.VERTICAL)
        rightSizer.Add(self.text,1,wx.ALL | wx.EXPAND,0)
        self.rightPanel.SetSizer(rightSizer)
        self.rightPanel.SetAutoLayout(True)
        rightSizer.Fit(self.rightPanel)
        
        lpID = wx.NewId()

        tID = wx.NewId()
        self.wordList = wx.ListCtrl(self.sp,tID,style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_SINGLE_SEL)
        self.wordList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelectWord)
        self.wordList.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.wordList.SetFont(font)
        self.wordList.InsertColumn(0,u"คำศัพท์")
        self.wordList.SetColumnWidth(0, 250)
        
        self.sp.SplitVertically(self.wordList,self.rightPanel,200)
        self.sp.SetSashSize(5)
        
        self.SetSizer(mainSizer)

        self.conn = self.ConnectDatabase()

        if not fontError:
            self.input.SetValue(u'')
                
    def LookupDictSQLite(self, word1, word2=None, prefix=False):
        return

    def ConnectDatabase(self):
        return
        
    def OnTextEntered(self, event):        
        return

    def SetupAdditionalToolbar(self, mainSizer):
        return

    def SetupFont(self):
        fontError = False
        try:
            font = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            font.SetFaceName('TF Chiangsaen')            
            self.input.SetFont(font)
        except wx.PyAssertionError, e:
            fontError = True
            font = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  
            self.input.SetFont(font)
            self.input.SetValue(u'กรุณาติดตั้งฟอนต์ TF Chiangsaen เพื่อการแสดงผลที่ถูกต้อง')

        try:
            self.text.SetFont(font)
        except wx.PyAssertionError, e:        
            font = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  
            self.text.SetFont(font)

        return font, fontError

    def SetContent(self,content):
        self.text.SetValue(content)

    def SetInput(self,text):
        self.input.SetValue(text)
        
    def OnClose(self, event):
        self.Hide()
        event.Skip()

    def OnSelectWord(self, event):
        self.currentItem =  event.m_itemIndex
        word = self.wordList.GetItemText(self.currentItem)
        item = self.LookupDictSQLite(word)
        if item != None:
            tran = item[1]
            self.text.SetValue(word+u'\n\n'+tran)
        event.Skip()

    def OnDoubleClick(self, event):
        word = self.wordList.GetItemText(self.currentItem)
        self.input.SetValue(word)
        event.Skip()

class EnglishDictWindow(DictWindow):

    def ConnectDatabase(self):
        return sqlite3.connect(constants.ENGLISH_DICT_DB)

    def OnTextEntered(self, event):
        text = self.input.GetValue().strip()
        self.wordList.DeleteAllItems()
        if text != '':
            items = self.LookupDictSQLite(text, None, prefix=True)
            if len(items) > 0:
                for i,item in enumerate(items):
                    self.wordList.InsertStringItem(i,item[0])
            else:
                self.text.SetValue(text + u'\n\n'+u'ไม่พบคำนี้ในพจนานุกรม')
        else:
            self.text.SetValue(text + u'\n'+u'กรุณาป้อนคำที่ต้องการค้นหา')
        event.Skip()

    def LookupDictSQLite(self, word1, word2=None, prefix=False):
        cursor = self.conn.cursor()
        word1 = self.ConvertToLowercase(word1)
        if prefix:
            cursor.execute("SELECT head,translation FROM english WHERE head LIKE ?", (word1+'%',))
            return cursor.fetchmany(size=50)
        else:
            cursor.execute("SELECT head,translation FROM english WHERE head = ?", (word1,))
            return cursor.fetchone()  

    def SetupFont(self):
        font = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  
        self.input.SetFont(font)
        self.text.SetFont(font)
        return font, True

    def ConvertToLowercase(self, headword):
        upperchars = u'ĀĪŪṄṂÑṬḌṆḶ'
        lowerchars = u'āīūṅṃñṭḍṇḷ'
        result = u''
        for c in headword:
            pos = upperchars.find(c)
            result += lowerchars[pos] if pos > -1 else c.lower()
        return result

    def SetupAdditionalToolbar(self, mainSizer):
        lowerSizer = wx.BoxSizer(wx.HORIZONTAL)        
        lowerChars = u'āīūṅṃñṭḍṇḷ'

        def OnCharButton(event):
            button = event.GetEventObject()
            self.input.SetValue(self.input.GetValue() + button.title)
            self.input.SetInsertionPointEnd()

        for button, c in ((wx.Button(self, wx.ID_ANY, c, size=(-1, -1)), c) for c in lowerChars):
            font = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  
            button.title = c
            button.SetFont(font)
            button.Bind(wx.EVT_BUTTON, OnCharButton)
            lowerSizer.Add(button, 1)
        
        mainSizer.Add(lowerSizer,0,wx.EXPAND | wx.ALL)
        mainSizer.Add((-1, 1), 0,wx.EXPAND | wx.ALL)


class ThaiDictWindow(DictWindow):

    def ConnectDatabase(self):
        return sqlite3.connect(constants.THAI_DICT_DB)

    def OnTextEntered(self, event):
        text = self.input.GetValue().strip()
        self.wordList.DeleteAllItems()
        if text != '':
            items = self.LookupDictSQLite(text, None, prefix=True)
            if len(items) > 0:
                for i,item in enumerate(items):
                    self.wordList.InsertStringItem(i,item[0])
            else:
                self.text.SetValue(text + u'\n\n'+u'ไม่พบคำนี้ในพจนานุกรม')
        else:
            self.text.SetValue(text + u'\n'+u'กรุณาป้อนคำที่ต้องการค้นหา')
        event.Skip()

    def LookupDictSQLite(self, word1, word2=None, prefix=False):
        cursor = self.conn.cursor()
        if prefix:
            cursor.execute("SELECT head,translation FROM thai WHERE head LIKE ?", (word1+'%',))
            return cursor.fetchmany(size=50)
        else:
            cursor.execute("SELECT head,translation FROM thai WHERE head = ?", (word1,))
            return cursor.fetchone()                        
            

class PaliDictWindow(DictWindow):
    
    def ConnectDatabase(self):
        conn = sqlite3.connect(constants.PALI_DICT_DB)
        return conn
        
    def OnTextEntered(self, event):
        text = self.input.GetValue().strip()

        text1 = text.replace(u'\u0e0d',u'\uf70f').replace(u'\u0e4d',u'\uf711').replace(u'ฐ',u'\uf700')
        text2 = text.replace(u'\u0e0d',u'\uf70f').replace(u'\u0e4d',u'\uf711')

        self.wordList.DeleteAllItems()

        if text != '':
            items = self.LookupDictSQLite(text1,text2,prefix=True)
            if len(items) > 0:
                for i,item in enumerate(items):
                    self.wordList.InsertStringItem(i,item[0])
            else:
                self.text.SetValue(text + u'\n\n'+u'ไม่พบคำนี้ในพจนานุกรม')
        else:
            self.text.SetValue(text + u'\n'+u'กรุณาป้อนคำที่ต้องการค้นหา')

        event.Skip()
        
    def LookupDictSQLite(self, word1, word2=None, prefix=False):
        cursor = self.conn.cursor()
        if prefix:
            if word2:                
                cursor.execute("SELECT * FROM p2t WHERE headword LIKE ? OR headword LIKE ? ", (word1+'%', word2+'%'))
            else:
                cursor.execute("SELECT * FROM p2t WHERE headword LIKE ?", (word1+'%', ))
            return cursor.fetchmany(size=50)
        else:
            if word2:
                cursor.execute("SELECT * FROM p2t WHERE headword = ? OR headword = ?", (word1, word2))
            else:
                cursor.execute("SELECT * FROM p2t WHERE headword = ?", (word1, ))
            return cursor.fetchone()            


class AuiBaseFrame(aui.AuiMDIChildFrame):
    
    def __init__(self, parent, *args, **kwargs):
        super(AuiBaseFrame, self).__init__(parent, *args, **kwargs)
        
        auiFlags = aui.AUI_MGR_DEFAULT
        if wx.Platform == '__WXGTK__' and aui.AUI_MGR_DEFAULT & aui.AUI_MGR_TRANSPARENT_HINT:
            auiFlags -= aui.AUI_MGR_TRANSPARENT_HINT
            auiFlags |= aui.AUI_MGR_VENETIAN_BLINDS_HINT
        self._mgr = aui.AuiManager(self, flags=auiFlags)
        self._mgr = aui.AuiManager(self)
        
        self.Bind(wx.EVT_CLOSE, self.OnAuiBaseClose)
        
    @property
    def AuiManager(self):
        return self._mgr
        
    def OnAuiBaseClose(self, event):
        appName = wx.GetApp().GetAppName()
        config = wx.Config(appName)
        perspective = self._mgr.SavePerspective()
        config.Write("perspective", perspective)
        event.Skip()
        
    def AddPane(self, pane, auiInfo):
        self._mgr.AddPane(pane, auiInfo)
        self._mgr.Update()
        
    def GetCenterPane(self):
        return self._mgr.GetPane("CenterPane")
        
    def SetCenterPane(self, pane, caption=False):
        info = aui.AuiPaneInfo()
        info = info.Center().Name("CenterPane")
        info = info.Dockable(False).CloseButton(False).CaptionVisible(caption)
        self._mgr.AddPane(pane, info)
        
    def LoadDefaultPerspective(self):
        appName = wx.GetApp().GetAppName()
        config = wx.Config(appName)
        perspective = config.Read("perspective")
        if perspective:
            self._mgr.LoadPerspective(perspective)

class MySearchCtrl(wx.SearchCtrl):
    
    MAX_SEARCH_HISTORY = 20
        
    def __init__(self, parent, logFile, value='', 
                 pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, 
                 delegate=None, lang=constants.LANG_THAI):
        super(MySearchCtrl, self).__init__(parent, wx.ID_ANY, value, 
                                           pos, size, style|wx.TE_PROCESS_ENTER)

        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
        self.Bind(wx.EVT_MENU_RANGE, self.OnMenuItem, id=0, id2=self.MAX_SEARCH_HISTORY-1)

        self._delegate = delegate
        self._logFile = logFile
        self._lang = lang

        self._searches = []
        self.LoadSearches()
            
    def OnTextEnter(self, event):
        text = self.GetValue().strip()
        if hasattr(self._delegate, 'Search') and self._delegate.Search(text):
            self.AppendSearch(text)
    
    def AppendSearch(self, text):
        if len(text.strip()) > 0:
            if text not in self._searches:
                self._searches.append(text)
            if len(self._searches) > self.MAX_SEARCH_HISTORY:
                del self._searches[0]
            self.SetMenu(self.MakeMenu())
        
    def OnMenuItem(self, event):
        text = self._searches[event.GetId()-1]
        self.SetValue(text)
        if hasattr(self._delegate, 'Search'):
            self._delegate.Search(text)

    def MakeMenu(self):
        font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        font.SetFaceName(constants.DEFAULT_FONT)

        menu = wx.Menu()
        item = wx.MenuItem(menu, wx.ID_ANY, _('Latest search'))
        item.SetFont(font)
        item.Enable(False)
        menu.AppendItem(item)

        for idx, txt in enumerate(self._searches):
            item = wx.MenuItem(menu, idx+1, txt)
            item.SetFont(font)
            menu.AppendItem(item)
        return menu
        
    def LoadSearches(self):
        if os.path.exists(self._logFile):            
            try:
                for text in codecs.open(self._logFile,'r','utf-8').readlines():
                    if text.strip() == '': continue 
                    self._searches.append(text.strip())
                    if len(self._searches) > self.MAX_SEARCH_HISTORY:
                        del self._searches[0]
            except UnicodeDecodeError,e:
                with codecs.open(self._logFile, 'w','utf-8') as out:
                    out.write('')
            menu = self.MakeMenu()
            self.SetMenu(menu)        

    def SaveSearches(self):
        if not os.path.exists(constants.CONFIG_PATH):
            os.makedirs(constants.CONFIG_PATH)
            
        with codecs.open(self._logFile, 'w', 'utf-8') as out:    
            for search in self._searches:
                if self._lang == constants.LANG_PALI:
                    search = utils.ConvertToPaliSearch(search)
                out.write(u'%s\n' % (search))
        
    @property
    def Language(self):
        return self._lang
        
    @Language.setter
    def Language(self, lang):
        self._lang = lang
        
    @property
    def Delegate(self):
        return self._delegate
    
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        
class ReadToolPanel(wx.Panel):

    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        
    @property
    def DataSource(self):
        return self._dataSource
        
    @DataSource.setter
    def DataSource(self, dataSource):
        self._dataSource = dataSource
        
    @property
    def CompareComboBox(self):
        return self._comboCompare
        
    @property
    def ForwardButton(self):
        return self._forwardButton
        
    @property
    def BackwardButton(self):
        return self._backwardButton
        
    @property
    def FontsButton(self):
        return self._fontsButton
        
    @property
    def IncreaseFontButton(self):
        return self._incFontButton
        
    @property
    def DecreaseFontButton(self):
        return self._decFontButton

    @property
    def BookListButton(self):
        return self._bookListButton
        
    @property
    def StarButton(self):
        return self._starButton
        
    @property
    def SearchButton(self):
        return self._searchButton

    @property
    def PrintButton(self):
        return self._printButton
        
    @property
    def SaveButton(self):
        return self._saveButton
        
    @property
    def PaliDictButton(self):
        return self._paliDictButton
        
    @property
    def ThaiDictButton(self):
        return self._thaiDictButton

    @property
    def EnglishDictButton(self):
        return self._englishDictButton
        
    @property
    def NotesButton(self):
        return self._notesButton

    @property
    def MarkButton(self):
        return self._markButton
        
    @property
    def ThemeComboBox(self):
        return self._themeComboBox
        
    def __init__(self, parent, dataSource, *args, **kwargs):
        super(ReadToolPanel, self).__init__(parent, *args, **kwargs)

        self._delegate = None
        self._dataSource = dataSource
        
        self._CreateAttributes()
        self._DoLayout()

    def _CreateAttributes(self):
        self._viewPanel = wx.Panel(self, wx.ID_ANY)
        viewSizer = wx.StaticBoxSizer(wx.StaticBox(self._viewPanel, wx.ID_ANY, u'อ่านทีละหน้า'), orient=wx.HORIZONTAL)
        self._backwardButton = wx.BitmapButton(self._viewPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.LEFT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._forwardButton = wx.BitmapButton(self._viewPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.RIGHT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        viewSizer.Add(self._backwardButton, flag=wx.ALIGN_CENTER)
        viewSizer.Add(self._forwardButton, flag=wx.ALIGN_CENTER)        
        self._viewPanel.SetSizer(viewSizer)
        self._viewPanel.Fit()
                
        self._comparePanel = wx.Panel(self, wx.ID_ANY)
        compareSizer = wx.StaticBoxSizer(wx.StaticBox(self._comparePanel, wx.ID_ANY, u'เทียบเคียงกับ'), orient=wx.HORIZONTAL)
        self._comboCompare = wx.ComboBox(self._comparePanel, wx.ID_ANY, 
            choices=self._dataSource.GetCompareChoices(), style=wx.CB_DROPDOWN|wx.CB_READONLY)
        compareSizer.Add(self._comboCompare, flag=wx.ALIGN_CENTER)
        self._comparePanel.SetSizer(compareSizer) 
        self._comparePanel.Fit()       

        # tools
        self._toolsPanel = wx.Panel(self, wx.ID_ANY)
        toolsSizer = wx.StaticBoxSizer(wx.StaticBox(self._toolsPanel, wx.ID_ANY, u'เครื่องมือ'), orient=wx.HORIZONTAL)
        
        self._searchButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SEARCH_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._searchButton.SetToolTip(wx.ToolTip(u'ค้นหาจากข้อความที่ถูกเลือก'))
        
        self._starButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.STAR_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._starButton.SetToolTip(wx.ToolTip(u'ที่คั่นหน้า'))

        self._notesButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.NOTES_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._notesButton.SetToolTip(wx.ToolTip(u'ค้นหาบันทึกข้อความเพิ่มเติม'))

        self._markButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.YELLOW_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._markButton.SetToolTip(wx.ToolTip(u'รายการไฮไลท์'))
                
        self._bookListButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.LAYOUT_IMAGE, wx.BITMAP_TYPE_GIF).Scale(32,32)))
        self._bookListButton.SetToolTip(wx.ToolTip(u'แสดง/ซ่อน หน้าต่างเลือกหนังสือ'))
                
        self._fontsButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.FONTS_IMAGE, wx.BITMAP_TYPE_PNG)), size=self._searchButton.GetSize())
        self._fontsButton.SetToolTip(wx.ToolTip(u'เปลี่ยนรูปแบบตัวหนังสือ'))
        
        self._incFontButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.INC_IMAGE, wx.BITMAP_TYPE_GIF)), size=self._searchButton.GetSize())
        self._incFontButton.SetToolTip(wx.ToolTip(u'เพิ่มขนาดตัวหนังสือ'))
        
        self._decFontButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.DEC_IMAGE, wx.BITMAP_TYPE_GIF)), size=self._searchButton.GetSize())
        self._decFontButton.SetToolTip(wx.ToolTip(u'ลดขนาดตัวหนังสือ'))
                
        self._saveButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SAVE_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)))
        self._saveButton.SetToolTip(wx.ToolTip(u'บันทึกข้อมูลลงไฟล์'))

        self._printButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.PRINT_IMAGE, wx.BITMAP_TYPE_PNG)))
        self._printButton.SetToolTip(wx.ToolTip(u'พิมพ์หน้าที่ต้องการ'))                        
        
        toolsSizer.Add(self._bookListButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))                
        toolsSizer.Add(self._searchButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))        
        toolsSizer.Add(self._starButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))        
        toolsSizer.Add(self._notesButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))        
        toolsSizer.Add(self._markButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))                
        toolsSizer.Add(self._fontsButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add(self._incFontButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add(self._decFontButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))                
        toolsSizer.Add(self._saveButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add(self._printButton, flag=wx.ALIGN_CENTER)
                
        self._toolsPanel.SetSizer(toolsSizer)
        self._toolsPanel.Fit()
        
        self._dictPanel = wx.Panel(self, wx.ID_ANY)
        dictSizer = wx.StaticBoxSizer(wx.StaticBox(self._dictPanel, wx.ID_ANY, u'พจนานุกรม'), orient=wx.HORIZONTAL)        
        self._paliDictButton = wx.BitmapButton(self._dictPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.PALI_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._paliDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรมบาลี-ไทย'))
        self._thaiDictButton = wx.BitmapButton(self._dictPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.THAI_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._thaiDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรม ภาษาไทย ฉบับราชบัณฑิตยสถาน'))        
        self._englishDictButton = wx.BitmapButton(self._dictPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.ENGLISH_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._englishDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรมบาลี-อังกฤษ'))        


        dictSizer.Add(self._paliDictButton, flag=wx.ALIGN_CENTER)
        dictSizer.Add(self._thaiDictButton, flag=wx.ALIGN_CENTER)
        dictSizer.Add(self._englishDictButton, flag=wx.ALIGN_CENTER)                
        dictSizer.Add((5, -1))        
        self._dictPanel.SetSizer(dictSizer)        
        self._dictPanel.Fit()
        
        themes = [u'ขาว', u'น้ำตาลอ่อน'] 
        self._themePanel = wx.Panel(self, wx.ID_ANY)
        themeSizer = wx.StaticBoxSizer(wx.StaticBox(self._themePanel, wx.ID_ANY, u'สีพื้นหลัง'), orient=wx.HORIZONTAL)
        self._themeComboBox = wx.ComboBox(self._themePanel, wx.ID_ANY, choices=themes, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self._themeComboBox.SetStringSelection(themes[utils.LoadTheme(constants.READ)])
        themeSizer.Add(self._themeComboBox, flag=wx.ALIGN_CENTER)
        self._themePanel.SetSizer(themeSizer)
        themeSizer.Fit(self._themePanel)                
        
    def _DoLayout(self):
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        mainSizer.Add(self._viewPanel, 0, wx.EXPAND)
        mainSizer.Add(self._comparePanel, 0, wx.EXPAND)
        mainSizer.Add(self._toolsPanel, 0, wx.EXPAND)
        mainSizer.Add(self._dictPanel, 0, wx.EXPAND)
        mainSizer.Add(self._themePanel, 0, wx.EXPAND)        

        self.SetSizer(mainSizer)
        
class ReadPanel(wx.Panel):

    def __init__(self, parent, code, index, font, delegate, *args, **kwargs):
        super(ReadPanel, self).__init__(parent, *args, **kwargs)

        self._parentSize = parent.GetSize()

        self._delegate = delegate
        self._code = code
        self._index = index
        
        self.Bind(wx.EVT_FIND, self.OnFind)
        self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)        
        
        self._CreateAttributes()
        self._DoLayout()

        self._font = utils.LoadFont(constants.READ_FONT) if font is None else font
        if self._font is None or not self._font.IsOk():
            self._font = self._body.GetFont()
            self._font.SetFaceName(constants.DEFAULT_FONT)
            self._font.SetPointSize(16)
        
        self.SetContentFont(self._font)
        self.SetBackgroundColour('white')

    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    @property
    def Slider(self):
        return self._slider

    @property
    def Body(self):
        return self._body

    @property
    def NotePanel(self):
        return self._notePanel

    @property
    def MarkButton(self):
        return self._markButton

    @property
    def UnmarkButton(self):
        return self._unmarkButton
        
    @property
    def ToggleNoteButton(self):
        return self._toggleNoteButton

    def SetContentFont(self, font):
        self._body.SetFont(font)
        
    def _CreateAttributes(self):
        divider = 2.0 if self._delegate.IsSmallScreen() else 1
        if 'wxMSW' in wx.PlatformInfo:
            self._title = wx.TextCtrl(self, wx.ID_ANY, size=(-1, 58/divider), style=wx.TE_READONLY|wx.NO_BORDER|wx.TE_MULTILINE|wx.TE_RICH2|wx.TE_CENTER|wx.TE_NO_VSCROLL)  
            self._title.SetFont(wx.Font(17, wx.DEFAULT, wx.NORMAL, wx.NORMAL))          
            self._title.SetForegroundColour(wx.BLUE)
            self._title.Bind(wx.EVT_RIGHT_DOWN, self.OnTextCtrlMouseRightDown)        
            self._title.Bind(wx.EVT_CONTEXT_MENU, lambda event: None)            
        else:
            self._title = wx.html.HtmlWindow(self, size=(-1, 58/divider), style=wx.html.HW_SCROLLBAR_NEVER)
            self._title.Bind(wx.EVT_RIGHT_DOWN, self.OnTextCtrlMouseRightDown)
        
        self._page = wx.html.HtmlWindow(self, size=(-1, 28), style=wx.html.HW_SCROLLBAR_NEVER)
        self._page.Bind(wx.EVT_RIGHT_DOWN, self.OnTextCtrlMouseRightDown)
        self._item = wx.html.HtmlWindow(self, size=(-1, 28), style=wx.html.HW_SCROLLBAR_NEVER)
        self._item.Bind(wx.EVT_RIGHT_DOWN, self.OnTextCtrlMouseRightDown)
        
        self._body = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY|wx.NO_BORDER|wx.TE_MULTILINE|wx.TE_RICH2)        
        self._body.SetForegroundColour(utils.LoadThemeForegroundColour(constants.READ))
        self._body.SetBackgroundColour(utils.LoadThemeBackgroundColour(constants.READ))
        self._body.Bind(wx.EVT_SET_FOCUS, self.OnTextBodySetFocus)
        self._body.Bind(wx.EVT_KILL_FOCUS, self.OnTextBodyKillFocus)
        self._body.Bind(wx.EVT_CHAR, self.OnCharKeyPress)
        self._body.Bind(wx.EVT_MOTION if 'wxMac' in wx.PlatformInfo else wx.EVT_LEFT_UP, self.OnTextBodySelect)
        self._body.Bind(wx.EVT_RIGHT_DOWN, self.OnTextCtrlMouseRightDown)        
        self._body.Bind(wx.EVT_CONTEXT_MENU, lambda event: None)

        self._slider = None
        if not self._delegate.IsSmallScreen():
            self._slider = wx.Slider(self, wx.ID_ANY, 1, 1, 100, style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)        
            self._slider.Bind(wx.EVT_SLIDER, self.OnSliderValueChange)
        
        self._paintPanel = wx.Panel(self, wx.ID_ANY)                

        self._markButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.YELLOW_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))
        self._markButton.SetToolTip(wx.ToolTip(u'ระบายสีข้อความที่ถูกเลือก'))
        self._markButton.Bind(wx.EVT_BUTTON, self.OnMarkButtonClick)
        
        self._unmarkButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.WHITE_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))
        self._unmarkButton.SetToolTip(wx.ToolTip(u'ลบสีข้อความที่ถูกเลือก'))
        self._unmarkButton.Bind(wx.EVT_BUTTON, self.OnUnmarkButtonClick)

        self._saveButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SAVE_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))
        self._saveButton.SetToolTip(wx.ToolTip(u'บันทึกการระบายสีข้อความ'))
        self._saveButton.Bind(wx.EVT_BUTTON, self.OnSaveButtonClick)        
        self._saveButton.Bind(wx.EVT_UPDATE_UI, self.OnUpdateSaveButton)
        
        self._clearButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.CLEAR_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))
        self._clearButton.SetToolTip(wx.ToolTip(u'ลบบันทึกการระบายสีข้อความทั้งหมด'))
        self._clearButton.Bind(wx.EVT_BUTTON, self.OnClearButtonClick)
        self._clearButton.Bind(wx.EVT_UPDATE_UI, self.OnUpdateClearButton)
        
        self._toggleNoteButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.NOTES_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))        
        self._toggleNoteButton.SetToolTip(wx.ToolTip(u'เปิด/ปิด บันทึกข้อความเพิ่มเติม'))
        self._toggleNoteButton.Bind(wx.EVT_BUTTON, self.OnToggleNoteButtonClick)

        self._toggleHeaderButton = wx.BitmapButton(self._paintPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.HEADER_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)))
        self._toggleHeaderButton.SetToolTip(wx.ToolTip(u'เปิด/ปิด ส่วนแสดงด้านบน'))
        self._toggleHeaderButton.Bind(wx.EVT_BUTTON, self.OnToggleHeaderClick)
        
        paintSizer = wx.BoxSizer(wx.HORIZONTAL)
        paintSizer.Add(self._markButton)
        paintSizer.Add(self._unmarkButton)
        paintSizer.Add((10,-1))
        paintSizer.Add(self._saveButton)
        paintSizer.Add(self._clearButton)
        paintSizer.Add((10,-1))
        paintSizer.Add(self._toggleNoteButton)  
        paintSizer.Add(self._toggleHeaderButton)              
        self._paintPanel.SetSizer(paintSizer)     
        
        self._notePanel = NotePanel(self, self._code, self._index)
        
        if self.Delegate.IsSmallScreen() or not utils.LoadNoteStatus():
            self._notePanel.Hide()
              
    def ExtraLayout(self):
        pass
                        
    def _DoLayout(self):
        self._mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        if 'wxMSW' in wx.PlatformInfo:
            self._mainSizer.Add(self._title, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        else:
            self._mainSizer.Add(self._title, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 5)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._page, 1, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT, 5)
        sizer.Add(self._item, 1, wx.EXPAND|wx.ALIGN_CENTER|wx.RIGHT, 5)
        
        self._mainSizer.Add(sizer, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.BOTTOM, 5)        

        if self._slider is not None:
            self._mainSizer.Add(self._slider, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        
        self._mainSizer.Add(self._paintPanel, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, 5)
        
        self._mainSizer.Add(self._body, 1, wx.EXPAND|wx.LEFT, 15)
        self.ExtraLayout()
        self._mainSizer.Add(self._notePanel, 0, wx.EXPAND)
        
        self.SetSizer(self._mainSizer)

    def OnTextBodySetFocus(self, event):
        self.Delegate.SetFocus(True, self._code, self._index)
        event.Skip()
        
    def OnTextBodyKillFocus(self, event):
        self.Delegate.SetFocus(False, self._code, self._index)        
        event.Skip()

    def OnTextBodySelect(self, event):
        self.Delegate.HandleTextSelection(self._body.GetStringSelection(), self._code, self._index)
        event.Skip()
        
    def OnTextCtrlMouseRightDown(self, event):
        self.Delegate.ShowContextMenu(event.GetEventObject(), event.GetPosition(), self._code, self._index)
        
    def OnSliderValueChange(self, event):
        self.Delegate.JumpToPage(event.GetSelection(), self._code, self._index)
        
    def OnMarkButtonClick(self, event):
        self.Delegate.MarkText(self._code, self._index)
        
    def OnUnmarkButtonClick(self, event):
        self.Delegate.UnmarkText(self._code, self._index)
        
    def OnClearButtonClick(self, event):
        self.Delegate.ClearMarkedText(self._code, self._index)
        
    def OnToggleNoteButtonClick(self, event):
        self.Delegate.ToggleNotePanel(self._code, self._index)
        
    def OnSaveButtonClick(self, event):
        self.Delegate.SaveMarkedText(self._code, self._index)
        
    def OnToggleHeaderClick(self, event):
        self.ToggleTitles()
        self.ToggleSlider()

    def OnFind(self, event):
        event.GetDialog().Destroy()       
        self._body.SetFocus()
        self.Delegate.DoFind(self._code, self._index, event.GetFindString(), self._body.GetValue(), event.GetFlags())
        
    def OnFindClose(self, event):
        event.GetDialog().Destroy()
        self._body.SetFocus()

    def OnCharKeyPress(self, event):
        try:
            self.Delegate.ProcessKeyCommand(event, event.GetKeyCode(), self._code, self._index)
        except ValueError, e:
            print e
        event.Skip()
            
    def OnUpdateClearButton(self, event):
        event.Enable(self.Delegate.HasSavedMark(self._code, self._index))
        
    def OnUpdateSaveButton(self, event):
        event.Enable(self.Delegate.HasMarkText(self._code, self._index))

    def SetBody(self, text):
        self._body.SetValue(text)
        font = self._body.GetFont()
        offset = 1 if 'wxMac' in wx.PlatformInfo else 0
        self._body.SetStyle(0, len(text)+offset, wx.TextAttr(utils.LoadThemeForegroundHex(constants.READ), 
            utils.LoadThemeBackgroundHex(constants.READ), font))
        
    def SetTitles(self, title1, title2):
        if 'wxMSW' in wx.PlatformInfo:
            self._title.SetValue(title1 if self._delegate.IsSmallScreen() else title1 + '\n' + title2)
        elif self._delegate.IsSmallScreen():
            self._title.SetPage(u'''<div align="center"><font color="#0000FF" size="5">%s</font></div>''' % (title1))            
        else:
            self._title.SetPage(u'''<div align="center"><font color="#0000FF" size="5">%s</font></div>
                <div align="center"><font color="#0000FF" size="5">%s</font></div>''' % (title1, title2))
    
    def SetPageNumber(self, number):        
        if number is None:
            self._page.SetPage('')
        else:
            text = _('Page') + ' ' + utils.ArabicToThai(unicode(number))
            self._page.SetPage(u'<div align="left"><font color="#378000" size="4">%s</font></div>' % (text))
        
    def SetItemNumber(self, *numbers):
        if len(numbers) == 0 or numbers[0] is None:
            self._item.SetPage('')
        else:
            text = _('Item') + ' ' + utils.ArabicToThai(unicode(numbers[0]))
            if len(numbers) > 1:
                text += ' - ' + utils.ArabicToThai(unicode(numbers[-1]))
            self._item.SetPage(u'<div align="right"><font color="#378000" size="4">%s</font></div>' % (text))

    def ToggleTitles(self):
        if self._title.IsShown():
            self._title.Hide()
            self._page.Hide()
            self._item.Hide()
        else:
            self._title.Show()
            self._page.Show()
            self._item.Show()
        self.Layout()

    def ToggleSlider(self):
        if self._slider is None:
            return
            
        if self._slider.IsShown():
            self._slider.Hide()
        else:
            self._slider.Show()
        self.Layout()

    def ToggleNotePanel(self):
        if self.NotePanel.IsShown():
            utils.SaveNoteStatus(False)
            self.NotePanel.Hide()
        else:
            utils.SaveNoteStatus(True)
            self.NotePanel.Show()
        self.Layout()

    def HideNotePanel(self):
        if self.NotePanel.IsShown():
            self.NotePanel.Hide()
            self.Layout()

    def ShowNotePanel(self):
        if not self.NotePanel.IsShown():
            self.NotePanel.Show()
            self.Layout()


class ReadWithReferencesPanel(ReadPanel):
    
    @property
    def Delegate(self):
        return self._delegate
    
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        self._refs.Delegate = delegate

    def SetContentFont(self, font):
        super(ReadWithReferencesPanel, self).SetContentFont(font)
        self._refs.SetStandardFonts(font.GetPointSize(), font.GetFaceName())

    def _CreateAttributes(self):
        super(ReadWithReferencesPanel, self)._CreateAttributes()
        self._refs = ReferencesWindow(self, size=(-1, 40))

    def ExtraLayout(self):
        self._mainSizer.Add(self._refs, 0, wx.EXPAND|wx.ALL, 5)
                
    def SetBody(self, text):
        super(ReadWithReferencesPanel, self).SetBody(text)
        refs = re.findall(ur'[–๐๑๒๓๔๕๖๗๘๙\s\-,]+/[–๐๑๒๓๔๕๖๗๘๙\s\-,]+/[–๐๑๒๓๔๕๖๗๘๙\s\-,]+', text, re.U)
        if len(refs) > 0:
            html = u'อ้างอิง:  '
            for ref in refs:
                ref = ref.strip().strip(u')').strip(u'(').strip(u',').strip()
                html += u'<a href="%s">%s</a>  '%(ref, ref)
            self._refs.Show()
            self._refs.SetPage(html)
        else:
            self._refs.Hide()
            self._refs.SetPage(u'')    
        self.Layout()

class NotePanel(wx.Panel):
    def __init__(self, parent, code, index, *args, **kwargs):
        super(NotePanel, self).__init__(parent, *args, **kwargs)
        self._code = code
        self._index = index
        self._CreateAttributes()
        self._BindAttributes()
        
    @property
    def BoldItem(self):
        return self._boldItem
        
    @property
    def ItalicItem(self):
        return self._italicItem
        
    @property
    def UnderlineItem(self):
        return self._underlineItem
        
    @property
    def AlignLeftItem(self):
        return self._alignLeftItem
    
    @property
    def AlignRightItem(self):
        return self._alignRightItem
        
    @property
    def CenterItem(self):
        return self._centerItem
        
    @property
    def IndentLessItem(self):
        return self._indentLessItem
        
    @property
    def IndentMoreItem(self):
        return self._indentMoreItem
        
    @property
    def FontItem(self):
        return self._fontItem
        
    @property
    def FontColorItem(self):
        return self._fontColorItem
        
    @property
    def SaveItem(self):
        return self._saveItem
        
    @property
    def KeyEnterItem(self):
        return self._keyEnterItem
        
    @property
    def NoteTextCtrl(self):
        return self._noteTextCtrl

    @property
    def View(self):
        return self.GetParent().GetParent()
        
    @property
    def Parent(self):
        return self.GetParent()
        
    @property
    def Delegate(self):
        return self.Parent.Delegate

    def _DoBind(self, item, handler, updateUI=None):
        self.View.Bind(wx.EVT_TOOL, handler, item)
        if updateUI is not None:
            self.View.Bind(wx.EVT_UPDATE_UI, updateUI, item)
        
    def _CreateAttributes(self):
        self.SetBackgroundColour('white')
        self._sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _('Notes')), orient=wx.VERTICAL)        
        self._noteTextCtrl = rt.RichTextCtrl(self, size=(-1, 50 if self.Parent.Delegate.IsSmallScreen() else 80), style=wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER)
        self._noteTextCtrl.SetModified(False)        

        self._toolBar = wx.ToolBar(self, style=wx.TB_HORIZONTAL|wx.NO_BORDER|wx.TB_FLAT)
                
        self._sizer.Add(self._noteTextCtrl, 1, wx.EXPAND)        
        self._sizer.Add(self._toolBar, 0, wx.EXPAND)
        
        self.SetSizer(self._sizer)
     
        self._toolBar.SetToolBitmapSize((22,22))
     
        self._saveItem = self._toolBar.AddTool(-1, images._rt_save.GetBitmap(), shortHelpString=_("Save"))
        self._toolBar.AddSeparator()
        self._boldItem = self._toolBar.AddTool(-1, images._rt_bold.GetBitmap(), isToggle=False, shortHelpString=_("Bold"))
        self._italicItem = self._toolBar.AddTool(-1, images._rt_italic.GetBitmap(), isToggle=True, shortHelpString=_("Italic"))
        self._underlineItem = self._toolBar.AddTool(-1, images._rt_underline.GetBitmap(), isToggle=True, shortHelpString=_("Underline"))   
        self._toolBar.AddSeparator()
        self._alignLeftItem = self._toolBar.AddTool(-1, images._rt_alignleft.GetBitmap(), isToggle=True, shortHelpString=_("Align Left"))
        self._centerItem = self._toolBar.AddTool(-1, images._rt_centre.GetBitmap(), isToggle=True, shortHelpString=_("Center"))
        self._alignRightItem = self._toolBar.AddTool(-1, images._rt_alignright.GetBitmap(), isToggle=True, shortHelpString=_("Align Right"))   
        self._toolBar.AddSeparator()
        self._indentLessItem = self._toolBar.AddTool(-1, images._rt_indentless.GetBitmap(), shortHelpString=_("Indent Less"))
        self._indentMoreItem = self._toolBar.AddTool(-1, images._rt_indentmore.GetBitmap(), shortHelpString=_("Indent More"))   
        self._toolBar.AddSeparator()
        self._fontItem = self._toolBar.AddTool(-1, images._rt_font.GetBitmap(), shortHelpString=_("Font"))
        self._fontColorItem = self._toolBar.AddTool(-1, images._rt_colour.GetBitmap(), shortHelpString=_("Font Color"))
        self._toolBar.AddSeparator()
        self._keyEnterItem = self._toolBar.AddTool(-1, images._rt_enter.GetBitmap(), shortHelpString=_("Newline"))
        
        self._toolBar.Realize()
        
    def _BindAttributes(self):
        self._DoBind(self._keyEnterItem, self.OnEnter)
        self._DoBind(self._indentLessItem, self.OnIndentLess)
        self._DoBind(self._indentMoreItem, self.OnIndentMore)
        self._DoBind(self._fontItem, self.OnFont)
        self._DoBind(self._fontColorItem, self.OnFontColor)                
    
        self._DoBind(self._saveItem, self.OnSave, self.OnUpdateSave)    
        self._DoBind(self._boldItem, self.OnBold, self.OnUpdateBold)
        self._DoBind(self._italicItem, self.OnItalic, self.OnUpdateItalic)
        self._DoBind(self._underlineItem, self.OnUnderline, self.OnUpdateUnderline)

        self._DoBind(self._alignLeftItem, self.OnAlignLeft, self.OnUpdateAlignLeft)
        self._DoBind(self._alignRightItem, self.OnAlignRight, self.OnUpdateAlignRight)
        self._DoBind(self._centerItem, self.OnCenter, self.OnUpdateCenter)
                    
    def OnSave(self, event):
        self.Delegate.SaveNoteText(self._code, self._index, self.Parent.NotePanel.NoteTextCtrl)
        
    def OnUpdateSave(self, event):
        event.Enable(self.Parent.NotePanel.NoteTextCtrl.IsModified())
                                        
    def OnBold(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyBoldToSelection()

    def OnUpdateBold(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionBold())        

    def OnEnter(self, event):
        self.Parent.NotePanel.NoteTextCtrl.Newline()
        
    def OnItalic(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyItalicToSelection()

    def OnUpdateItalic(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionItalics())

    def OnUnderline(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyUnderlineToSelection()

    def OnUpdateUnderline(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionUnderlined())

    def OnAlignLeft(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(wx.TEXT_ALIGNMENT_LEFT)

    def OnUpdateAlignLeft(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionAligned(wx.TEXT_ALIGNMENT_LEFT))

    def OnAlignRight(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(wx.TEXT_ALIGNMENT_RIGHT)

    def OnUpdateAlignRight(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionAligned(wx.TEXT_ALIGNMENT_RIGHT))

    def OnCenter(self, event):
        self.Parent.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(wx.TEXT_ALIGNMENT_CENTRE)

    def OnUpdateCenter(self, event):
        event.Check(self.Parent.NotePanel.NoteTextCtrl.IsSelectionAligned(wx.TEXT_ALIGNMENT_CENTRE))

    def OnIndentLess(self, event):
        self.Delegate.IndentLessNoteText(self.Parent.NotePanel.NoteTextCtrl)

    def OnIndentMore(self, event):
        self.Delegate.IndentMoreNoteText(self.Parent.NotePanel.NoteTextCtrl)

    def OnFont(self, event):
        self.Delegate.ApplyFontToNoteText(self.Parent.NotePanel.NoteTextCtrl)

    def OnFontColor(self, event):
        self.Delegate.ApplyFontColorToNoteText(self.Parent.NotePanel.NoteTextCtrl)    
        
        
class SearchToolPanel(wx.Panel):
    
    def __init__(self, parent, font, *args, **kwargs):
        super(SearchToolPanel, self).__init__(parent, *args, **kwargs)
        self._delegate = None
        self._font = font
        self._CreateAttributes()        
        self._DoLayout()
        
    @property
    def Delegate(self):
        return self._delegate
                
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        self._text.Delegate = delegate                
                
    @property
    def SearchCtrl(self):
        return self._text

    @property
    def AboutButton(self):
        return self._aboutButton

    @property
    def ForwardButton(self):
        return self._nextButton
        
    @property
    def BackwardButton(self):
        return self._prevButton
        
    @property
    def FontsButton(self):
        return self._fontsButton
        
    @property
    def SearchButton(self):
        return self._findButton
        
    @property
    def VolumesRadio(self):
        return self._volumesRadio
        
    @property
    def LanguagesComboBox(self):
        return self._langComboBox

    @property
    def ThemeComboBox(self):
        return self._themeComboBox

    @property
    def ReadButton(self):
        return self._readButton
        
    @property
    def CheckBox(self):
        return self._checkBox

    @property
    def ExportButton(self):
        return self._exportButton
        
    @property
    def ImportButton(self):
        return self._importButton
        
    @property
    def NikhahitButton(self):
        return self._nikhahitButton
        
    @property
    def ThothanButton(self):
        return self._thothanButton
        
    @property
    def YoyingButton(self):
        return self._yoyingButton

    @property
    def NotesButton(self):
        return self._notesButton
        
    @property
    def StarButton(self):
        return self._starButton
        
    @property
    def PaliDictButton(self):
        return self._paliDictButton
        
    @property
    def ThaiDictButton(self):
        return self._thaiDictButton

    @property
    def EnglishDictButton(self):
        return self._englishDictButton

    @property
    def SearchAndCompareButton(self):
        return self._searchAndCompareButton

    @property
    def BuddhawajOnly(self):
        return self._buddhawajOnly
        
    def _DoLayout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        topSizer.Add(self._symbolPanel, flag=wx.ALIGN_CENTER)
        topSizer.Add(self._fontsButton, flag=wx.ALIGN_CENTER)
        topSizer.Add((5,5))
        topSizer.Add(self._text, 1, wx.ALIGN_CENTER|wx.RIGHT, 3)
        topSizer.Add(self._buddhawajOnly, 0, wx.ALIGN_CENTER|wx.RIGHT, 5)        
        topSizer.Add(self._findButton, flag=wx.ALIGN_CENTER)
        topSizer.Add(self._volumesRadio, 0 ,wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 5)        
        topSizer.Add(self._aboutButton, 0, flag=wx.ALIGN_CENTER)
        
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer.Add(self._langPanel, 0, flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        bottomSizer.Add((5,5))
        bottomSizer.Add(self._readButton, flag=wx.ALIGN_BOTTOM)
        bottomSizer.Add((5,5))        
        bottomSizer.Add(self._checkBox, flag=wx.ALIGN_CENTER)
        bottomSizer.Add((10,5))
        bottomSizer.Add(self._prevButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)    
        bottomSizer.Add(self._nextButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self._starButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._notesButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)        
        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self._exportButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._importButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)            
        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self._paliDictButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._thaiDictButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._englishDictButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)            
        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self._searchAndCompareButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self._themePanel, 0, flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        
        mainSizer.Add(topSizer, 1, flag=wx.EXPAND|wx.ALIGN_BOTTOM)
        mainSizer.Add(bottomSizer, 0, flag=wx.EXPAND|wx.ALIGN_BOTTOM)
        
        self.SetSizer(mainSizer)

            
    def _CreateAttributes(self):
        self._text = MySearchCtrl(self, constants.LOG_FILE)        
        if 'wxMac' not in wx.PlatformInfo and self._font != None and self._font.IsOk():
            self._font.SetPointSize(16)
            self._text.SetFont(self._font)
        else:   
            font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            font.SetFaceName('Tahoma')            
            self._text.SetFont(font)

        self._buddhawajOnly = wx.CheckBox(self, wx.ID_ANY, label=u'เฉพาะพุทธวจน')
        self._buddhawajOnly.Disable()

        langs = constants.LANGS
        self._langPanel = wx.Panel(self, wx.ID_ANY)
        langSizer = wx.StaticBoxSizer(wx.StaticBox(self._langPanel, wx.ID_ANY, u'เลือก'), orient=wx.HORIZONTAL)
        self._langComboBox = wx.ComboBox(self._langPanel, wx.ID_ANY, choices=langs, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self._langComboBox.SetStringSelection(langs[0])
        langSizer.Add(self._langComboBox)
        self._langPanel.SetSizer(langSizer)
        langSizer.Fit(self._langPanel)
        
        self._volumesRadio = wx.RadioBox(self, wx.ID_ANY, _('Choose volumes'), choices=[_('All'), _('Custom')], majorDimension=2)
        
        self._findButton = buttons.GenBitmapTextButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SEARCH_IMAGE, wx.BITMAP_TYPE_PNG).Scale(16,16)), _('Search'), size=(65,35))
        
        self._symbolPanel = wx.Panel(self, wx.ID_ANY)
        symbolSizer = wx.StaticBoxSizer(wx.StaticBox(self._symbolPanel, wx.ID_ANY, _('Special characters')), orient=wx.HORIZONTAL)

        self._nikhahitButton = wx.BitmapButton(self._symbolPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.NIKHAHIT_IMAGE, wx.BITMAP_TYPE_GIF).Scale(16,16)))         

        self._thothanButton = wx.BitmapButton(self._symbolPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.THOTHAN_IMAGE, wx.BITMAP_TYPE_GIF).Scale(16,16)))                 

        self._yoyingButton = wx.BitmapButton(self._symbolPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.YOYING_IMAGE, wx.BITMAP_TYPE_GIF).Scale(16,16)))         
        symbolSizer.Add(self._nikhahitButton)
        symbolSizer.Add(self._thothanButton)
        symbolSizer.Add(self._yoyingButton)
        self._symbolPanel.SetSizer(symbolSizer)        
        if 'wxMac' in wx.PlatformInfo:
            self._symbolPanel.Hide()         
        
        self._fontsButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.FONTS_IMAGE, wx.BITMAP_TYPE_PNG)), size=(-1, 40))
        self._fontsButton.SetToolTip(wx.ToolTip(_('Change font')))
        
        self._prevButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.LEFT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        
        self._nextButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.RIGHT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)))
        
        self._prevButton.Disable()
        self._nextButton.Disable()
        
        self._importButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.IMPORT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._importButton.SetToolTip(wx.ToolTip(_('Import data')))
        
        self._exportButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.EXPORT_IMAGE, wx.BITMAP_TYPE_PNG)))         
        self._exportButton.SetToolTip(wx.ToolTip(_('Export data')))
        
        self._readButton = wx.BitmapButton(self, wx.ID_ANY, wx.BitmapFromImage(wx.Image(constants.READ_IMAGE, wx.BITMAP_TYPE_PNG)))
            
        self._aboutButton = wx.BitmapButton(self, wx.ID_ANY, wx.BitmapFromImage(wx.Image(constants.ABOUT_IMAGE, wx.BITMAP_TYPE_PNG)))
        self._aboutButton.SetToolTip(wx.ToolTip(_('About E-Tipitaka')))        
        
        self._checkBox = wx.CheckBox(self, wx.ID_ANY, label=u'เปิดหน้าใหม่ทุกครั้ง')
                
        self._starButton = wx.BitmapButton(self, wx.ID_ANY, wx.BitmapFromImage(wx.Image(constants.STAR_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._starButton.SetToolTip(wx.ToolTip(u'ที่คั่นหน้า'))

        self._notesButton = wx.BitmapButton(self, wx.ID_ANY, wx.BitmapFromImage(wx.Image(constants.NOTES_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._notesButton.SetToolTip(wx.ToolTip(u'ค้นหาบันทึกข้อความเพิ่มเติม'))
                                
        self._paliDictButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.PALI_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._paliDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรมบาลี-ไทย'))
        
        self._thaiDictButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.THAI_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._thaiDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรม ภาษาไทย ฉบับราชบัณฑิตยสถาน'))                        
                
        self._englishDictButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.ENGLISH_DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._englishDictButton.SetToolTip(wx.ToolTip(u'พจนานุกรมบาลี-อังกฤษ'))                        

        self._searchAndCompareButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SEARCH_AND_COMPARE_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._searchAndCompareButton.SetToolTip(wx.ToolTip(u'ค้นหาพร้อมจับคู่เลขข้อ'))                        

        themes = [u'ขาว', u'น้ำตาลอ่อน'] 
        self._themePanel = wx.Panel(self, wx.ID_ANY)
        themeSizer = wx.StaticBoxSizer(wx.StaticBox(self._themePanel, wx.ID_ANY, u'สีพื้นหลัง'), orient=wx.HORIZONTAL)
        self._themeComboBox = wx.ComboBox(self._themePanel, wx.ID_ANY, choices=themes, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self._themeComboBox.SetStringSelection(themes[utils.LoadTheme(constants.SEARCH)])
        themeSizer.Add(self._themeComboBox, flag=wx.ALIGN_CENTER)
        self._themePanel.SetSizer(themeSizer)
        themeSizer.Fit(self._themePanel)                
                
class ResultsWindow(wx.html.HtmlWindow):
    
    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    def __init__(self, parent, delegate=None, *args, **kwargs):
        super(ResultsWindow, self).__init__(parent, *args, **kwargs)
        self._delegate = delegate        
        
    def OnLinkClicked(self, link):                                    
        cmd, body = link.GetHref().split(':')
        if cmd == 'n':
            current, per, total = map(int, body.split(u'_'))
            if hasattr(self._delegate, 'ShowResults'):
                self._delegate.ShowResults(current)
        elif cmd == 's':
            if hasattr(self._delegate, 'Search'):
                self._delegate.Search(body)
        elif cmd == 'p':
            if hasattr(self._delegate, 'SaveScrollPosition'):
                self._delegate.SaveScrollPosition(self.GetScrollPos(wx.VERTICAL))            
            volume, page, code, now, per, total, idx = body.split(u'_')
            if hasattr(self._delegate, 'Read'):
                self._delegate.Read(code, int(volume), int(page), int(idx))
        elif cmd == 'note':
            if hasattr(self._delegate, 'SaveScrollPosition'):
                self._delegate.SaveScrollPosition(self.GetScrollPos(wx.VERTICAL))                        
            idx, volume, page, code = body.split(u'_')
            if hasattr(self._delegate, 'TakeNote'):
                self._delegate.TakeNote(code, int(volume), int(page), int(idx))
                
class ReferencesWindow(wx.html.HtmlWindow):    
            
    def __init__(self, *args, **kwargs):
        super(ReferencesWindow, self).__init__(*args, **kwargs)        
        self._delegate = None
        
    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    def OnLinkClicked(self, link):
        href = link.GetHref()
        dlg = wx.SingleChoiceDialog(self.Parent, 
            u'พระไตรปิฎก', u'เทียบเคียง', constants.COMPARE_CHOICES, wx.CHOICEDLG_STYLE)
        dlg.SetSize((250,280))
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            tokens = map(unicode.strip,href.split('/'))
            volume = utils.ThaiToArabic(tokens[0])
            item = utils.ThaiToArabic(re.split(r'[–\-,\s]+', tokens[2])[0])
            if hasattr(self._delegate, 'OnLinkToReference'):
                self._delegate.OnLinkToReference(constants.COMPARE_CODES[dlg.GetSelection()], int(volume), int(item))
        dlg.Destroy()

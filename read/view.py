#-*- coding:utf-8 -*-

import wx
import os, sys, os.path
import widgets, constants
from widgets import AuiBaseFrame
from wx.aui import AuiPaneInfo

import i18n
_ = i18n.language.ugettext

class ReadPanelCreator(object):
    @staticmethod
    def create(parent, code, font, delegate, mainWindow=False):
        if code == constants.THAI_FIVE_BOOKS_CODE:
            return widgets.ReadWithReferencesPanel(parent, code if not mainWindow else None, font, delegate)
        return widgets.ReadPanel(parent, code if not mainWindow else None, font, delegate)

class ViewComponentsCreator(object):
    @staticmethod
    def create(code, parent):
        if code == constants.THAI_FIVE_BOOKS_CODE:
            return ThaiFiveBooksViewComponents(parent)
        if code == constants.THAI_MAHACHULA_CODE:
            return ThaiMahaChulaViewComponents(parent)
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
        
class View(AuiBaseFrame):    
    
    def __init__(self, parent, title, code):
        super(View, self).__init__(parent, wx.ID_ANY, size=(1024, 768), title=title)
            
        self._dataSource = None
        self._delegate = None
        
        self._components = ViewComponentsCreator.create(code, self)
        self._code = code                
        self._readPanel = None
        self._comparePanel = {}
        self._font = None

    @property
    def Font(self):
        return self._font
        
    @Font.setter
    def Font(self, font):
        self._font
        self._readPanel.SetContentFont(font)
        for code in self._comparePanel:
            self._comparePanel[code].SetContentFont(font)

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

    def _PostInit(self):            
        self._readPanel = ReadPanelCreator.create(self, self._code, self._font, self._delegate, mainWindow=True)
        self._readPanel.Delegate = self._delegate
        self._readPanel.SetPageNumber(None)
        self._readPanel.SetItemNumber(None)

        self._toolPanel = widgets.ReadToolPanel(self, self._dataSource)        
        self._listPanel = self._CreateBookListPanel()        
        
        self.SetCenterPane(self._readPanel, caption=True)

        info = AuiPaneInfo().CaptionVisible(False).Resizable(False)
        info = info.FloatingSize((740, 65)).MinSize((740, 65)).Top().Layer(0)
        self.AddPane(self._toolPanel, info.Name('Tool'))

        info = AuiPaneInfo().CaptionVisible(False).TopDockable(False).BottomDockable(False)
        info = info.BestSize((250, 768)).FloatingSize((250, 768)).MinSize((0, 768)).Left().Layer(1)
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
            self._comparePanel[code] = ReadPanelCreator.create(self, code, self._font, self._delegate)
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
        info = self.AuiManager.GetPane('BookList')
        info.Show()
        self.AuiManager.Update()

    def ToggleBookList(self):
        info = self.AuiManager.GetPane('BookList')
        info.Hide() if info.IsShown() else info.Show()            
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
        
    def FormatText(self, formatter, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        font = readPanel.Body.GetFont()
        fontSize = font.GetPointSize()

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
        
    def UpdateSlider(self, value, minimum, maximum, code=None):
        readPanel = self._readPanel if code is None else self._comparePanel[code]
        readPanel.Slider.SetMin(minimum)
        readPanel.Slider.SetMax(maximum)
        readPanel.Slider.SetValue(value)
        
    def Start(self):
        self._PostInit()
        self._components.Filter(self)
        self.CenterOnScreen()
        self.Show()        

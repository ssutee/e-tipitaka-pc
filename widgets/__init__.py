#-*- coding:utf-8 -*-

import wx
import wx.aui as aui
import wx.lib.buttons as buttons
import wx.html
import os, os.path, sys, codecs
import constants, utils
import i18n
_ = i18n.language.ugettext

class AuiBaseFrame(wx.Frame):
    
    def __init__(self, parent, *args, **kwargs):
        super(AuiBaseFrame, self).__init__(parent, *args, **kwargs)
        
        auiFlags = aui.AUI_MGR_DEFAULT
        if wx.Platform == '__WXGTK__' and aui.AUI_MGR_DEFAULT & aui.AUI_MGR_TRANSPARENT_HINT:
            auiFlags -= aui.AUI_MGR_TRANSPARENT_HINT
            auiFlags |= aui.AUI_MGR_VENETIAN_BLINDS_HINT
        self._mgr = aui.AuiManager(self, flags=auiFlags)
        
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
            for text in codecs.open(self._logFile,'r','utf-8').readlines():
                if text.strip() == '': continue 
                self._searches.append(text.strip())
                if len(self._searches) > self.MAX_SEARCH_HISTORY:
                    del self._searches[0]
            menu = self.MakeMenu()
            self.SetMenu(menu)        

    def SaveSearches(self):
        if not os.path.exists(constants.CONFIG_PATH):
            os.makedirs(constants.CONFIG_PATH)
        out = codecs.open(self._logFile, 'w', 'utf-8')
        for search in self._searches:
            if self._lang == constants.LANG_PALI:
                search = utils.ConvertToPaliSearch(search)
            out.write(u'%s\n' % (search))
        out.close()    
        
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

class BookListPanel(wx.Panel):
    
    def __ini__(self, parent, *args, **kwargs):
        super(BookListPanel, self).__init__(parent, *args, **kwargs)
        
        self._delegate = None
        self._CreateAttributes()
        self._DoLayout()
        
    def _CreateAttributes(self):
        pass
        
    def _DoLayout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(mainSizer)
        
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
                
        self._layoutButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.LAYOUT_IMAGE, wx.BITMAP_TYPE_GIF).Scale(32,32)))
        self._layoutButton.SetToolTip(wx.ToolTip(u'แสดง/ซ่อน หน้าต่างเลือกหนังสือ'))
                
        self._fontsButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.FONTS_IMAGE, wx.BITMAP_TYPE_PNG)), size=self._searchButton.GetSize())
        self._fontsButton.SetToolTip(wx.ToolTip(u'เปลี่ยนรูปแบบตัวหนังสือ'))
        
        self._incFontButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.INC_IMAGE, wx.BITMAP_TYPE_GIF)), size=self._searchButton.GetSize())
        self._incFontButton.SetToolTip(wx.ToolTip(u'เพิ่มขนาดตัวหนังสือ'))
        
        self._decFontButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.DEC_IMAGE, wx.BITMAP_TYPE_GIF)), size=self._searchButton.GetSize())
        self._decFontButton.SetToolTip(wx.ToolTip(u'เพิ่มขนาดตัวหนังสือ'))
                
        self._saveButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.SAVE_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)))
        self._saveButton.SetToolTip(wx.ToolTip(u'บันทึกข้อมูลลงไฟล์'))

        self._printButton = wx.BitmapButton(self._toolsPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.PRINT_IMAGE, wx.BITMAP_TYPE_PNG)))
        self._printButton.SetToolTip(wx.ToolTip(u'พิมพ์หน้าที่ต้องการ'))                
                
        toolsSizer.Add(self._searchButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))        
        toolsSizer.Add(self._starButton, flag=wx.ALIGN_CENTER)
        toolsSizer.Add((5,-1))        
        toolsSizer.Add(self._layoutButton, flag=wx.ALIGN_CENTER)
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
        self._dictButton = wx.BitmapButton(self._dictPanel, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.DICT_IMAGE, wx.BITMAP_TYPE_PNG))) 
        self._dictButton.SetToolTip(wx.ToolTip(u'พจนานุกรมบาลี-ไทย'))
        dictSizer.Add(self._dictButton, flag=wx.ALIGN_CENTER)        
        dictSizer.Add((15, -1))        
        self._dictPanel.SetSizer(dictSizer)        
        self._dictPanel.Fit()

    def _DoLayout(self):
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        mainSizer.Add(self._viewPanel, 0, wx.EXPAND)
        mainSizer.Add(self._comparePanel, 0, wx.EXPAND)
        mainSizer.Add(self._toolsPanel, 0, wx.EXPAND)
        mainSizer.Add(self._dictPanel, 0, wx.EXPAND)

        self.SetSizer(mainSizer)
        
class ReadPanel(wx.Panel):

    def __init__(self, parent, code, font, delegate, *args, **kwargs):
        super(ReadPanel, self).__init__(parent, *args, **kwargs)

        self._delegate = delegate
        self._code = code
        
        self._font = font
        self._CreateAttributes()
        self._DoLayout()

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
        
    def _CreateAttributes(self):
        self._title = wx.html.HtmlWindow(self, size=(-1, 80), style=wx.html.HW_SCROLLBAR_NEVER|wx.html.HW_NO_SELECTION)
        
        self._page = wx.html.HtmlWindow(self, size=(-1, 40), style=wx.html.HW_SCROLLBAR_NEVER|wx.html.HW_NO_SELECTION)
        self._item = wx.html.HtmlWindow(self, size=(-1, 40), style=wx.html.HW_SCROLLBAR_NEVER|wx.html.HW_NO_SELECTION)
        
        self._body = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY|wx.NO_BORDER|wx.TE_MULTILINE|wx.TE_RICH2)
        self._body.Bind(wx.EVT_SET_FOCUS, self.OnTextBodySetFocus)
        self._body.Bind(wx.EVT_KILL_FOCUS, self.OnTextBodyKillFocus)
        self._body.Bind(wx.EVT_CHAR, self.OnCharKeyPress)
        self._font = utils.LoadFont(constants.READ_FONT)
        if self._font != None and self._font.IsOk():
            self._body.SetFont(self._font)
        else:
            self._font = self._body.GetFont()
            self._font.SetPointSize(16)
            self._body.SetFont(self._font)
        
        self._slider = wx.Slider(self, wx.ID_ANY, 1, 1, 100, style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self._slider.Bind(wx.EVT_SLIDER, self.OnSliderValueChange)

    def _DoLayout(self):
        self._mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        self._mainSizer.Add(self._title, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 5)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._page, 1, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT, 5)
        sizer.Add(self._item, 1, wx.EXPAND|wx.ALIGN_CENTER|wx.RIGHT, 5)
        
        self._mainSizer.Add(sizer, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.BOTTOM, 5)        

        self._mainSizer.Add(self._slider, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        
        self._mainSizer.Add(self._body, 10, wx.EXPAND|wx.LEFT, 15)
        
        self.SetSizer(self._mainSizer)
        
    def OnTextBodySetFocus(self, event):
        self.Delegate.SetFocus(True, self._code)
        
    def OnTextBodyKillFocus(self, event):
        self.Delegate.SetFocus(False, self._code)        
        
    def OnSliderValueChange(self, event):
        self.Delegate.JumpToPage(event.GetSelection(), self._code)
        
    def OnCharKeyPress(self, event):
        try:
            self.Delegate.ProcessKeyCommand(event.GetKeyCode(), self._code)
        except ValueError, e:
            pass

    def SetBody(self, text):
        self._body.SetValue(text)
        
    def SetTitles(self, title1, title2):
        self._title.SetPage(u'''<div align="center"><font color="#0000FF" size="6">%s</font></div>
            <div align="center"><font color="#0000FF" size="6">%s</font></div>''' % (title1, title2))
    
    def SetPageNumber(self, number):        
        if number is None:
            self._page.SetPage('')
        else:
            text = _('Page') + ' ' + utils.ArabicToThai(unicode(number))
            self._page.SetPage(u'<div align="left"><font color="#378000" size="5">%s</font></div>' % (text))
        
    def SetItemNumber(self, *numbers):
        if len(numbers) == 0 or numbers[0] is None:
            self._item.SetPage('')
        else:
            text = _('Item') + ' ' + utils.ArabicToThai(unicode(numbers[0]))
            if len(numbers) > 1:
                text += ' - ' + utils.ArabicToThai(unicode(numbers[-1]))
            self._item.SetPage(u'<div align="right"><font color="#378000" size="5">%s</font></div>' % (text))

class ReadWithReferencesPanel(ReadPanel):
    
    @property
    def Delegate(self):
        return self._delegate
    
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        self._refs.Delegate = delegate

    def _CreateAttributes(self):
        super(ReadWithReferencesPanel, self)._CreateAttributes()
        
        self._refs = ReferencesWindow(self)
        
    def _DoLayout(self):
        super(ReadWithReferencesPanel, self)._DoLayout()
        
        self._mainSizer.Add(self._refs, 1, wx.EXPAND|wx.ALL, 5)

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
    def ReadButton(self):
        return self._readButton
        
    @property
    def CheckBox(self):
        return self._checkBox

    def _DoLayout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        topSizer.Add(self._symbolPanel, flag=wx.ALIGN_CENTER)
        topSizer.Add(self._fontsButton, flag=wx.ALIGN_CENTER)
        topSizer.Add((5,5))
        topSizer.Add(self._text, 1, wx.ALIGN_CENTER|wx.RIGHT, 3)
        topSizer.Add(self._findButton, flag=wx.ALIGN_CENTER)
        topSizer.Add((5,5))
        topSizer.Add(self._aboutButton, 0, flag=wx.ALIGN_CENTER)
        
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer.Add(self._readButton, flag=wx.ALIGN_BOTTOM)
        bottomSizer.Add((5,5))        
        bottomSizer.Add(self._checkBox, flag=wx.ALIGN_CENTER)
        bottomSizer.Add((10,5))
        bottomSizer.Add(self._langPanel, 0, flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        bottomSizer.Add((5,5))
        bottomSizer.Add(self._volumesRadio, 0 ,flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        bottomSizer.Add((5,5))
        bottomSizer.Add(self._prevButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)    
        bottomSizer.Add(self._nextButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add((20,-1), 0)
        bottomSizer.Add(self._exportButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._importButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)    
        
        mainSizer.Add(topSizer, 1, flag=wx.EXPAND|wx.ALIGN_BOTTOM)
        mainSizer.Add(bottomSizer, 0, flag=wx.EXPAND|wx.ALIGN_BOTTOM)
        
        self.SetSizer(mainSizer)

            
    def _CreateAttributes(self):
        self._text = MySearchCtrl(self, constants.LOG_FILE)        
        if 'wxMac' not in wx.PlatformInfo and self._font != None and self._font.IsOk():
            font.SetPointSize(16)
            self._text.SetFont(self._font)
        else:   
            self._text.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, u''))

        langs = [_('Thai Royal'), _('Pali Siam'), _('Thai Mahamakut'), _('Thai Mahachula'), _('Thai Five Books')] 
        self._langPanel = wx.Panel(self, wx.ID_ANY)
        langSizer = wx.StaticBoxSizer(wx.StaticBox(self._langPanel, wx.ID_ANY, _('Languages')), orient=wx.HORIZONTAL)
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
            wx.BitmapFromImage(wx.Image(constants.IMPORT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._importButton.SetToolTip(wx.ToolTip(_('Import data')))
        
        self._exportButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.EXPORT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)))         
        self._exportButton.SetToolTip(wx.ToolTip(_('Export data')))
        
        self._readButton = buttons.GenBitmapTextButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.BOOKS_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)), _('Read'), size=(-1, 57))
        self._aboutButton = wx.Button(self, wx.ID_ANY, _('About'), size=wx.DefaultSize)        
        self._aboutButton.SetToolTip(wx.ToolTip(_('About E-Tipitaka')))        
        
        self._checkBox = wx.CheckBox(self, wx.ID_ANY, label=u'เปิดหน้าใหม่ทุกครั้ง')
                
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
            u'พระไตรปิฎก', u'เทียบเคียง', 
            [u'ภาษาไทย ฉบับหลวง', u'บาลีสยามรัฐ'], wx.CHOICEDLG_STYLE)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            tokens = map(unicode.strip,href.split('/'))
            volume = utils.ThaiToArabic(tokens[0])
            item = utils.ThaiToArabic(re.split(r'[–\-,\s]+', tokens[2])[0])
            if hasattr(self._delegate, 'OnLinkToReference'):
                self._delegate.OnLinkToReference(
                    u'thai' if dlg.GetStringSelection() == u'ภาษาไทย ฉบับหลวง' else u'pali', 
                    int(volume), int(item))
        dlg.Destroy()

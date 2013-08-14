#-*- coding:utf-8 -*-

import wx
import wx.aui as aui
import wx.lib.buttons as buttons
import wx.html

import os, os.path, sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PARENT_DIR)

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
        
    def OnAuiBaseClose(self, event):
        appName = wx.GetApp().GetAppName()
        config = wx.Config(appName)
        perspective = self._mgr.SavePerspective()
        config.Write("perspective", perspective)
        event.Skip()
        
    def AddPane(self, pane, auiInfo):
        self._mgr.AddPane(pane, auiInfo)
        self._mgr.Update()
        
    def SetCenterPane(self, pane):
        info = aui.AuiPaneInfo()
        info = info.Center().Name("CenterPane")
        info = info.Dockable(False).CaptionVisible(False)
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
        if hasattr(self._delegate, 'DoSearch') and self._delegate.DoSearch(text):
            self.AppendSearch(text)
    
    def AppendSearch(self, text):
        if len(text.strip()) > 0:
            if text not in self._searches:
                self._searches.append(text)
            if len(self._searches) > self.MAX_SEARCH_HISTORY:
                del self._searches[0]
            self.SetMenu(self.MakeMenu())
        
    def OnMenuItem(self, event):
        text = self._searches[event.GetId()]
        self.SetValue(text)
        if hasattr(self._delegate, 'DoSearch'):
            self._delegate.DoSearch(text)

    def MakeMenu(self):
        font = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        font.SetFaceName(constants.DEFAULT_FONT)

        menu = wx.Menu()
        item = wx.MenuItem(menu, wx.ID_ANY, _('Latest search'))
        item.SetFont(font)
        item.Enable(False)
        menu.AppendItem(item)

        for idx, txt in enumerate(self._searches):
            item = wx.MenuItem(menu, idx, txt)
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

class SearchToolPanel(wx.Panel):
    
    def __init__(self, parent, font, *args, **kwargs):
        super(SearchToolPanel, self).__init__(parent, *args, **kwargs)
        self._delegate = None
        self._CreateAttributes(font)        
        self._DoLayout()

    @property
    def Delegate(self):
        return self._delegate
                
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        self.text.Delegate = delegate                
                
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
        bottomSizer.Add(self._langPanel, flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        bottomSizer.Add(self._volumesRadio ,flag=wx.ALIGN_BOTTOM|wx.EXPAND)
        bottomSizer.Add((5,5))
        bottomSizer.Add(self._prevButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)    
        bottomSizer.Add(self._nextButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add((20,-1), 0)
        bottomSizer.Add(self._exportButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)
        bottomSizer.Add(self._importButton, flag=wx.ALIGN_BOTTOM|wx.SHAPED)    
        
        mainSizer.Add(topSizer, 1, flag=wx.EXPAND)
        mainSizer.Add(bottomSizer, 1, flag=wx.EXPAND)
        
        self.SetSizer(mainSizer)
            
    def _CreateAttributes(self, font):
        self._text = MySearchCtrl(self, constants.LOG_FILE)        
        if 'wxMac' not in wx.PlatformInfo and font != None and font.IsOk():
            font.SetPointSize(16)
            self._text.SetFont(font)
        else:   
            self._text.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, u''))

        langs = [_('Thai Royal'), _('Pali Siam'), _('Thai Mahamakut'), _('Thai Mahachula'), _('Thai Five Books')] 
        self._langPanel = wx.Panel(self, wx.ID_ANY)
        langSizer = wx.StaticBoxSizer(wx.StaticBox(self._langPanel, wx.ID_ANY, _('Languages')), orient=wx.HORIZONTAL)
        self._langComboBox = wx.ComboBox(self._langPanel, wx.ID_ANY, choices=langs, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self._langComboBox.SetStringSelection(langs[0])
        langSizer.Add(self._langComboBox)
        self._langPanel.SetSizer(langSizer)
        
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
        
        self._importButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.IMPORT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32))) 
        self._importButton.SetToolTip(wx.ToolTip(_('Import data')))
        
        self._exportButton = wx.BitmapButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.EXPORT_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)))         
        self._exportButton.SetToolTip(wx.ToolTip(_('Export data')))
        
        self._readButton = buttons.GenBitmapTextButton(self, wx.ID_ANY, 
            wx.BitmapFromImage(wx.Image(constants.BOOKS_IMAGE, wx.BITMAP_TYPE_PNG).Scale(32,32)), _('Read'), size=(-1, 40))
        self._aboutButton = wx.Button(self, wx.ID_ANY, _('About'), size=wx.DefaultSize)        
        self._aboutButton.SetToolTip(wx.ToolTip(_('About E-Tipitaka')))        
        
class ResultsWindow(wx.html.HtmlWindow):
    
    def __init__(self, parent, lang, *args, **kwargs):
        super(ResultsWindow, self).__init__(parent, *args, **kwargs)
        

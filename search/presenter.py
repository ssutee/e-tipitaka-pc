#-*- coding:utf-8 -*-

import search.model
from dialogs import AboutDialog, UpdateDialog, NoteManagerDialog
import wx, zipfile, os, json
import wx.richtext as rt
from utils import BookmarkManager
import i18n
_ = i18n.language.ugettext

import constants, utils, threads 

import pony.orm
from pony.orm import db_session

from distutils.version import LooseVersion, StrictVersion
import settings, widgets

import read.model
import read.interactor
import read.view
import read.presenter

class Presenter(object):
    def __init__(self, model, view, interactor):
        rt.RichTextBuffer.AddHandler(rt.RichTextXMLHandler())
        self._presenters = {}
        self._scrollPosition = 0
        self._shouldOpenNewWindow = False
        self._refreshHistoryList = True
        self._paliDictWindow = None
        self._thaiDictWindow = None
        self._delegate = None
        self._model = model        
        self._model.Delegate = self
        self._view = view
        self._view.Delegate = self
        self._bookmarkManager = BookmarkManager(self._view, self._model.Code)
        interactor.Install(self, view)
        self.RefreshHistoryList(0)
        self.CheckNewUpdate()
        self._view.Start()
         
    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, value):
        self._delegate = value

    @property
    def BookmarkItems(self):
        return self._bookmarkManager.Items
                
    @property
    def Model(self):
        return self._model

    def ShowAboutDialog(self):
        dialog = AboutDialog(self._view)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
        
    def ShowFontDialog(self):
        curFont = utils.LoadFont(constants.SEARCH_FONT)
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        if curFont != None:
            fontData.SetInitialFont(curFont)
        dialog = wx.FontDialog(self._view, fontData)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            if font.IsOk():
                utils.SaveFont(font, constants.SEARCH_FONT)
                self._view.Font = font
                if 'wxMac' not in wx.PlatformInfo:
                    size = font.GetPointSize()
                    font.SetPointSize(16)
                    self._view.SearchCtrl.SetFont(font)
                    font.SetPointSize(size)
                self._view.ResultsWindow.SetStandardFonts(font.GetPointSize(),font.GetFaceName())
        dialog.Destroy()
        
    def Search(self, keywords=None, code=None, refreshHistoryList=True):
        self._refreshHistoryList = refreshHistoryList
        
        if not keywords:
            keywords = self._view.SearchCtrl.GetValue()

        if len(keywords.strip()) == 0 or len(keywords.replace('+',' ').strip()) == 0:
            return True
        
        if code is not None and constants.CODES.index(code) != self._view.TopBar.LanguagesComboBox.GetSelection():
            self._view.TopBar.LanguagesComboBox.SetSelection(constants.CODES.index(code))
            self.SelectLanguage(constants.CODES.index(code))
        
        self._view.SearchCtrl.SetValue(keywords)
        self._model.Search(keywords)
        
        return True
                
    def OpenBook(self, volume=1, page=0, code=None):        
        self.Read(self._model.Code if code is None else code, volume, page, 0, section=1, shouldHighlight=False, showBookList=True)

    def Read(self, code, volume, page, idx, section=None, shouldHighlight=True, showBookList=False):        
        self._model.Read(code, volume, page, idx)
        self._delegate.Read(code, volume, page, idx, section, shouldHighlight, showBookList, self._shouldOpenNewWindow)        

    def BringToFront(self):
        self._view.Raise()
        self._view.Iconize(False)        
            
    def SaveHistory(self, code):
        self._model.SaveHistory(code)

    def OnReadWindowClose(self, code, presenter):
        self.SaveHistory(code)
        self._delegate.OnReadWindowClose(code, presenter)

    def OnReadWindowOpenPage(self, volume, page, code):
        self._model.Skim(volume, page, code)

    def SearchWillStart(self, keywords):
        self._view.DisableSearchControls()
        self._view.SetPage('<html><body bgcolor="%s">'%(utils.LoadThemeBackgroundHex(constants.SEARCH)) + _('Searching data, please wait...') + '</body></html>')
        self._view.SetStatusText(_('Searching data'), 0)
        self._view.SetStatusText('', 1)
        self._view.SetStatusText('', 2)
        self._view.DisableHistoryControls()
                
    def SearchDidFinish(self, results, keywords):    
        self._model.LoadHistory(self._model.ConvertSpecialCharacters(keywords), self._model.Code, len(results))

        self._model.Results = results
        
        if len(results) > 0:
           self.ShowResults(1)
        else:
            html = '<html><body bgcolor="%s">%s</body></html>' % (utils.LoadThemeBackgroundHex(constants.SEARCH), self._model.NotFoundMessage()+self._model.MakeHtmlSuggestion(found=False))
            self._view.SetPage(html)
            self._view.EnableSearchControls()
            self._view.EnableHistoryControls()                
            
        self._view.SetStatusText('', 0)
        self._view.SetStatusText(_('Found %d pages') % (len(results)), 1)
        
        if self._refreshHistoryList:
            self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), 
                self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())
                
    def ShowResults(self, current):
        self._model.Display(current)
        
    def SelectLanguage(self, index):
        self._model = search.model.SearchModelCreator.Create(self, index)
        self._view.VolumesRadio.Disable() if index == 4 or index == 5 or index == 6 else self._view.VolumesRadio.Enable()
        self.RefreshHistoryList(index, self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())
        self._bookmarkManager = BookmarkManager(self._view, self._model.Code)

    def SelectTheme(self, index):
        utils.SaveTheme(index, constants.SEARCH)
        self._view.ResultsWindow.SetPage(u'<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
        self._model.ReloadDisplay()
        
    def SelectVolumes(self, index):
        
        def OnDismiss(ret, volumes):
            if ret == wx.ID_OK:
                self._model.SelectedVolumes = volumes
                self._model.Mode = constants.MODE_CUSTOM
            else:
                self._view.VolumesRadio.SetSelection(0)
                self._model.Mode = constants.MODE_ALL
        
        if index == 1:
            volumes = self._model.SelectedVolumes if len(self._model.SelectedVolumes) > 0 else self._model.Volumes            
            self._view.ShowVolumesDialog(self._model, volumes, OnDismiss)
        else:
            self._model.Mode = constants.MODE_ALL
                
    def HasDisplayResult(self, key):
        return self._model.HasDisplayResult(key)
        
    def SaveDisplayResult(self, items, key):
        self._model.SaveDisplayResult(items, key)
        
    def SaveScrollPosition(self, position):
        self._scrollPosition = position
        
    def DisplayDidProgress(self, progress):
        self._view.SetProgress((progress * 100.0) / constants.ITEMS_PER_PAGE)
        
    def DisplayWillStart(self):
        self._view.SetPage(u'<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
        self._view.SetProgress(0)
        self._view.SetStatusText(_('Displaying results'), 0)
        
    def DisplayDidFinish(self, key, current):
        html = self._model.MakeHtmlResults(current)
        self._view.SetPage(html)
        self._view.SetProgress(0)        
        mark = self._model.GetMark(current)
        self._view.SetStatusText('', 0)        
        self._view.SetStatusText(_('Search results') + ' %d - %d' % (mark[0]+1, mark[1]) , 2)
        self._view.EnableSearchControls()
        self._view.EnableHistoryControls()    

        self._view.BackwardButton.Disable() if current == 1 else self._view.BackwardButton.Enable()
        self._view.ForwardButton.Disable() if current == self._model.GetPages() else self._view.ForwardButton.Enable()
        
        self._view.ScrollTo(self._scrollPosition)
                    
    def NextPagination(self):
        self._model.DisplayNext()
        
    def PreviousPagination(self):
        self._model.DisplayPrevious()
                    
    def SetOpenNewWindow(self, flag):
        self._shouldOpenNewWindow = flag
    
    @db_session
    def RefreshHistoryList(self, index, alphabetSort=True, text=''):
        selected = self._view.HistoryList.GetStringSelection()
        items = search.model.Model.GetHistoryListItems(index, alphabetSort, text)
        self._view.SetHistoryListItems(items)
        if selected in items:
            self._view.HistoryList.EnsureVisible(items.index(selected))
            self._view.HistoryList.SetSelection(items.index(selected))        
    
    @db_session                
    def ReloadHistory(self, position):
        h = list(search.model.Model.GetHistories(self._view.TopBar.LanguagesComboBox.GetSelection(), 
            self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue()))[position]
        self.Search(h.keywords, refreshHistoryList=False)
    
    def ExportData(self):
        from datetime import datetime        
        zipFile = 'backup-%s.etz' % (datetime.now().strftime('%Y-%m-%d'))
        dlg = wx.FileDialog(self._view, _('Save data'), constants.HOME, zipFile, constants.ETZ_TYPE, wx.SAVE|wx.OVERWRITE_PROMPT)        
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            with zipfile.ZipFile(os.path.join(dlg.GetDirectory(), dlg.GetFilename()), 'w') as fz:                
                rootlen = len(constants.DATA_PATH) + 1
                for base, dirs, files in os.walk(constants.DATA_PATH):
                    for filename in files:
                            fn = os.path.join(base, filename)
                            fz.write(fn, fn[rootlen:])                
            wx.MessageBox(_('Export data complete'), u'E-Tipitaka')
        dlg.Destroy()
        
    def ImportData(self):
        ret = 0
        dlg = wx.FileDialog(self._view, _('Choose import data'), constants.HOME, '', constants.ETZ_TYPE, wx.OPEN|wx.CHANGE_DIR)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:        
            with zipfile.ZipFile(os.path.join(dlg.GetDirectory(), dlg.GetFilename()), 'r') as fz:
                fz.extractall(constants.DATA_PATH)            
            # relocate old version data file
            for filename in os.listdir(constants.DATA_PATH):
                fullpath = os.path.join(constants.DATA_PATH, filename)
                if os.path.isfile(fullpath) and filename.split('.')[-1] == 'fav':
                    os.rename(fullpath, os.path.join(constants.BOOKMARKS_PATH, filename))
                elif os.path.isfile(fullpath) and filename.split('.')[-1] == 'log':
                    os.rename(fullpath, os.path.join(constants.BOOKMARKS_PATH, '.'.join(filename.split('.')[:-1])+'.cfg'))
                elif os.path.isfile(fullpath) and not fullpath.endswith('.sqlite'):
                    os.rename(fullpath, os.path.join(constants.CONFIG_PATH, os.path.basename(filename)))                                            
            wx.MessageBox(_('Import data complete'), u'E-Tipitaka')
            self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())                    
        dlg.Destroy()
        
    def InputSpecialCharacter(self, charCode):
        text = self._view.SearchCtrl.GetValue()
        ins = self._view.SearchCtrl.GetInsertionPoint()
        text = text[:ins] + charCode + text[ins:]
        self._view.SearchCtrl.SetValue(text)
        self._view.SearchCtrl.SetFocus()
        self._view.SearchCtrl.SetInsertionPoint(ins+1)

    def SortHistoryList(self, selection):
        self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), selection==0, self._view.FilterCtrl.GetValue())
        
    def FilterHistoryList(self, text):
        self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), 
            self._view.SortingRadioBox.GetSelection()==0, text)

    def DeleteSelectedHistoryItem(self):
        if self._view.HistoryList.GetSelection() == -1: return
        
        with db_session:
            h = list(search.model.Model.GetHistories(self._view.TopBar.LanguagesComboBox.GetSelection(), 
                self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue()))[self._view.HistoryList.GetSelection()]
            h.delete()

        with db_session:
            self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), 
                self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())
                
    def Download(self):
        import webbrowser
        url = constants.DOWNLOAD_SRC_URL
        if 'wxMac' in wx.PlatformInfo:
            url = constants.DOWNLOAD_OSX_URL
        elif 'wxMSW' in wx.PlatformInfo:
            url = constants.DOWNLOAD_MSW_URL
        webbrowser.open_new(url)
        
    def SkipThisVersion(self, version):
        with open(constants.SKIP_VERSION_FILE, 'w') as f:
            f.write(version)
                
    def CheckNewUpdateDidFinish(self, version):
        skipped = open(constants.SKIP_VERSION_FILE).read() if os.path.exists(constants.SKIP_VERSION_FILE) else None

        if skipped == version or StrictVersion(version) <= StrictVersion(settings.VERSION): return
        
        dlg = UpdateDialog(self._view, settings.VERSION, version)
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            self.Download()
        elif ret == wx.ID_NO:
            self.SkipThisVersion(version)
        dlg.Destroy()
                
    def CheckNewUpdate(self):
        threads.CheckNewUpdateThread(self).start()
        
    def SaveSearches(self):
        self._view.SearchCtrl.SaveSearches()

    # def Close(self):
    #     utils.SaveSearchWindowPosition(self._view)
    #     for code in self._presenters:
    #         utils.SaveReadWindowPosition(self._presenters[code][0].View)
    #         self._model.SaveHistory(code)

    def ShowBookmarkPopup(self, x, y):
        self._view.ShowBookmarkPopup(x,y)
        
    def ShowNotesManager(self):        
        dlg = NoteManagerDialog(self._view)
        if dlg.ShowModal() == wx.ID_OK:
            volume, page, code = dlg.Result
            self.OpenBook(volume, page, code)
        dlg.Destroy()
        
        
    def LoadBookmarks(self, menu):

        def OnBookmark(event):
            item = self._view.GetBookmarkMenuItem(event.GetId())
            text = utils.ThaiToArabic(item.GetText())
            tokens = text.split(' ')
            volume, page = int(tokens[1]), int(tokens[3])            
            self.OpenBook(volume, page)

        self._bookmarkManager.Load()
        self._bookmarkManager.MakeMenu(menu, OnBookmark)
        
    def OpenPaliDict(self):

        def OnDictClose(event):
            self._paliDictWindow = None
            event.Skip()

        if self._paliDictWindow is None:
            self._paliDictWindow = widgets.PaliDictWindow(self._view)
            self._paliDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._paliDictWindow.SetTitle(u'พจนานุกรม บาลี-ไทย')

        self._paliDictWindow.Show()        
        self._paliDictWindow.Raise()

    def OpenThaiDict(self):

        def OnDictClose(event):
            self._thaiDictWindow = None
            event.Skip()

        if self._thaiDictWindow is None:
            self._thaiDictWindow = widgets.ThaiDictWindow(self._view)
            self._thaiDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._thaiDictWindow.SetTitle(u'พจนานุกรม ภาษาไทย ฉบับราชบัณฑิตยสถาน')

        self._thaiDictWindow.Show()        
        self._thaiDictWindow.Raise()

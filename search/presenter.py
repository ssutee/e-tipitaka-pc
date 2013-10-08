import search.model
from dialogs import AboutDialog
import wx

import i18n
_ = i18n.language.ugettext

import constants, utils 

from pony.orm import db_session

import read.model
import read.interactor
import read.view
import read.presenter

class Presenter(object):
    def __init__(self, model, view, interactor):
        self._presenters = {}
        self._scrollPosition = 0
        self._shouldOpenNewWindow = False
        self._model = model        
        self._model.Delegate = self
        self._view = view
        self._view.Delegate = self
        interactor.Install(self, view)
        self.RefreshHistoryList(0)
        self._view.Start()
         
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
        
    def Search(self, keywords=None):
        if not keywords:
            keywords = self._view.SearchCtrl.GetValue()

        if len(keywords.strip()) == 0 or len(keywords.replace('+',' ').strip()) == 0:
            return True
        
        self._view.SearchCtrl.SetValue(keywords)
        self._model.Search(keywords)
        
        return True
        
    def OpenBook(self):
        self.Read(self._model.Code, 1, 0, 0, section=1, shouldHighlight=False)

    def Read(self, code, volume, page, idx, section=None, shouldHighlight=True):
        self._model.Read(code, volume, page, idx)
        presenter = None if self._presenters.get(code) is None else self._presenters.get(code)[0]
        if not presenter or self._shouldOpenNewWindow:
            model = read.model.Model(code)
            view = read.view.View(self._view, self._model.Code, code)
            interactor = read.interactor.Interactor()
            presenter = read.presenter.Presenter(model, view, interactor, code)
            presenter.Delegate = self
            if code not in self._presenters:
                self._presenters[code] = [presenter]
            else:
                self._presenters[code] += [presenter]
        else:
            presenter.BringToFront() 
        presenter.Keywords = self._model.Keywords if shouldHighlight else None
        presenter.OpenBook(volume, page, section)
            
    def OnReadWindowClose(self, code):
        if code in self._presenters:
            self._model.SaveHistory(code)
            del self._presenters[code]  
            
    def OnReadWindowOpenPage(self, volume, page, code):
        self._model.Skim(volume, page, code)

    def SearchWillStart(self, keywords):
        self._view.DisableSearchControls()
        self._view.SetPage(_('Searching data, please wait...'))
        self._view.SetStatusText(_('Searching data'), 0)
        self._view.SetStatusText('', 1)
        self._view.SetStatusText('', 2)
                
    def SearchDidFinish(self, results, keywords):
        
        self._model.LoadHistory(keywords, self._model.Code, len(results))

        self._model.Results = results
        
        if len(results) > 0:
           self.ShowResults(1)
        else:
            self._view.SetPage(self._model.NotFoundMessage()+self._model.MakeHtmlSuggestion(found=False))
            
        self._view.SetStatusText('', 0)
        self._view.SetStatusText(_('Found %d pages') % (len(results)), 1)
        
        self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection())
        
    def ShowResults(self, current):
        self._model.Display(current)
        
    def SelectLanguage(self, index):
        self._model = search.model.SearchModelCreator.create(self, index)
        self._view.VolumesRadio.Disable() if index == 4 else self._view.VolumesRadio.Enable()
        self.RefreshHistoryList(index)
        
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
        self._view.SetPage(u'')
        self._view.SetProgress(0)
        self._view.SetStatusText(_('Displaying results'), 0)
        
    def DisplayDidFinish(self, key, current):
        self._view.SetPage(self._model.MakeHtmlResults(current))
        self._view.SetProgress(0)        
        mark = self._model.GetMark(current)
        self._view.SetStatusText('', 0)        
        self._view.SetStatusText(_('Search results') + ' %d - %d' % (mark[0]+1, mark[1]) , 2)
        self._view.EnableSearchControls()

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
    def RefreshHistoryList(self, index):
        items = search.model.Model.GetHistoryListItems(index)
        self._view.SetHistoryListItems(items)
    
    @db_session                
    def ReloadHistory(self, position):
        h = list(search.model.Model.GetHistories(self._view.TopBar.LanguagesComboBox.GetSelection()))[position]
        self.Search(h.keywords)
    
    def Close(self):
        self._view.SearchCtrl.SaveSearches()

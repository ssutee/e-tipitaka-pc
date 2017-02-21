#-*- coding:utf-8 -*-

import search.model
from dialogs import AboutDialog, UpdateDialog, NoteManagerDialog, SimpleFontDialog, NoteDialog, MarkManagerDialog
import wx, zipfile, os, json, tempfile
import xml.etree.ElementTree as ET
import wx.richtext as rt
from utils import BookmarkManager
import i18n
_ = i18n.language.ugettext

import constants, utils, threads 

import pony.orm
from pony.orm import db_session
import sqlite3

from distutils.version import LooseVersion, StrictVersion
import settings, widgets

import read.model
import read.interactor
import read.view
import read.presenter

import codecs

class Presenter(object):
    def __init__(self, model, view, interactor):
        rt.RichTextBuffer.AddHandler(rt.RichTextXMLHandler())
        self._presenters = {}
        self._scrollPosition = 0
        self._shouldOpenNewWindow = False
        self._canBeClosed = False
        self._refreshHistoryList = True
        self._searchingBuddhawaj = False
        self._paliDictWindow = None
        self._thaiDictWindow = None
        self._englishDictWindow = None
        self._searchAndCompareWindow = None
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
        
    @property
    def CanBeClosed(self):
        return self._canBeClosed
    
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
        dialog = SimpleFontDialog(self._view, fontData) if 'wxMac' in wx.PlatformInfo else wx.FontDialog(self._view, fontData)
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
        self._searchingBuddhawaj = self._view.BuddhawajOnly.IsChecked()
        self._model.Search(keywords, buddhawaj=self._searchingBuddhawaj)
        
        return True
                
    def OpenBook(self, volume=1, page=0, code=None):        
        self.Read(self._model.Code if code is None else code, volume, page, 0, section=1, shouldHighlight=False, showBookList=True)

    def Read(self, code, volume, page, idx, section=None, shouldHighlight=True, showBookList=False):        
        # update reading status
        self._model.Read(code, volume, page, idx)
        # open new page
        self._delegate.Read(code, volume, page, section, shouldHighlight, showBookList, self._shouldOpenNewWindow)        

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
        self._view.VolumesRadio.Enable() if self._model.HasVolumeSelection() else self._view.VolumesRadio.Disable()

        self._view.BuddhawajOnly.Enable() if self._model.HasBuddhawaj() else self._view.BuddhawajOnly.Disable()
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
        h = search.model.Model.GetHistories(self._view.TopBar.LanguagesComboBox.GetSelection(), 
            self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())[position]
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

    def ImportHistory(self, keywords, total, code, read, skimmed, pages, notes):
        conn = sqlite3.connect(constants.DATA_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM History WHERE keywords=? AND code=?', (keywords, code))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO History (keywords, total, code, read, skimmed, pages, notes) VALUES (?,?,?,?,?,?,?)',(keywords, total, code, read, skimmed, pages, notes))
        conn.commit()
        conn.close()        

    def ImportPCData(self, path):
        if os.path.exists(os.path.join(tempfile.gettempdir(), 'note.sqlite')):
            os.remove(os.path.join(tempfile.gettempdir(), 'note.sqlite'))

        if os.path.exists(os.path.join(tempfile.gettempdir(), 'data.sqlite')):
            os.remove(os.path.join(tempfile.gettempdir(), 'data.sqlite'))
 
        with zipfile.ZipFile(path, 'r') as fz:
            for filename in fz.namelist():
                if filename.endswith('.sqlite'):
                    fz.extract(filename, tempfile.gettempdir())
                else:
                    fz.extract(filename, constants.DATA_PATH)

        if os.path.exists(os.path.join(tempfile.gettempdir(), 'note.sqlite')):
            conn = sqlite3.connect(os.path.join(tempfile.gettempdir(), 'note.sqlite'))
            cursor = conn.cursor()
            cursor.execute('PRAGMA user_version=2')
            cursor.execute('SELECT volume,page,code,filename,text FROM Note')
            for volume, page, code, xmlfile, text in cursor.fetchall():
                self.WriteXmlNoteFile(volume, page, code, text)
            conn.commit()
            conn.close()
        
        if os.path.exists(os.path.join(tempfile.gettempdir(), 'data.sqlite')):
            conn = sqlite3.connect(os.path.join(tempfile.gettempdir(), 'data.sqlite'))
            cursor = conn.cursor()
            cursor.execute('PRAGMA user_version=4')
            cursor.execute('SELECT keywords,total,code,read,skimmed,pages,notes FROM History')
            for keywords, total, code, read, skimmed, pages, notes in cursor.fetchall():
                self.ImportHistory(keywords, total, code, read, skimmed, pages, notes)
            conn.commit()
            conn.close()

        # relocate old version data file
        for filename in os.listdir(constants.DATA_PATH):
            fullpath = os.path.join(constants.DATA_PATH, filename)
            if os.path.isfile(fullpath) and filename.split('.')[-1] == 'fav':
                os.rename(fullpath, os.path.join(constants.BOOKMARKS_PATH, filename))
            elif os.path.isfile(fullpath) and filename.split('.')[-1] == 'log':
                os.rename(fullpath, os.path.join(constants.BOOKMARKS_PATH, '.'.join(filename.split('.')[:-1])+'.cfg'))
            elif os.path.isfile(fullpath) and not fullpath.endswith('.sqlite'):
                os.rename(fullpath, os.path.join(constants.CONFIG_PATH, os.path.basename(filename)))    

    @db_session
    def WriteXmlNoteFile(self, volume, page, code, note):
        if volume == 0 or page == 0 or len(note) == 0 or code == None:
            return

        xml_note_file = os.path.join(constants.NOTES_PATH, code, '%02d-%04d.xml' % (volume, page))
        if not os.path.exists(os.path.join(constants.NOTES_PATH, code)):
            os.makedirs(os.path.join(constants.NOTES_PATH, code))

        ET.register_namespace('', 'http://www.wxwidgets.org')
        if os.path.exists(xml_note_file):
            tree = ET.parse(xml_note_file)
            root = tree.getroot()
        else:
            root = ET.fromstring(constants.XML_NOTE_TEMPLATE)
            tree = ET.ElementTree(root)

        para_layout = root.find('{http://www.wxwidgets.org}paragraphlayout')

        original_text = u''
        for para in para_layout:
            for text in para:
                original_text += text.text
            original_text += u'\n'

        for line in note.split('\n'):
            para_node = ET.SubElement(para_layout, '{http://www.wxwidgets.org}paragraph')
            text_node = ET.SubElement(para_node, '{http://www.wxwidgets.org}text')
            text_node.text = line if len(line) > 0 else ' '

        if original_text.strip().find(note.strip()) == -1:
            tree.write(xml_note_file)

        conn = sqlite3.connect(constants.NOTE_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Note WHERE volume=? AND page=? AND code=?', (volume, page, code))        
        text = original_text+ '\n' + note if original_text != '' else note
        found = cursor.fetchone()
        if found and original_text.strip().find(note.strip()) == -1:
            cursor.execute('UPDATE Note SET text=?,filename=? WHERE volume=? AND page=? AND code=?', (text, xml_note_file, volume, page, code))
        elif not found:
            cursor.execute('INSERT INTO Note (volume,page,code,filename,text) VALUES (?,?,?,?,?)', (volume,page,code,xml_note_file,text))
        conn.commit()
        conn.close()

    def ProcessIOSData(self, text):
        jsonobj = json.loads(text)
        if jsonobj.get('version', 1) < 2:
            return False
        
        for item in jsonobj.get('bookmarks', []):
            volume = item.get('volume', 0)
            page = item.get('page', 0)
            code = constants.IOS_CODE_TABLE.get(item.get('code', -1)) 
            note = item.get('note', '')

            self.WriteXmlNoteFile(volume, page, code, note)

        return True

    def ImportIOSData(self, path):
        if path.split()[-1] == 'etz':
            with zipfile.ZipFile(path, 'r') as fz:
                for filename in fz.namelist():
                    self.ProcessIOSData(fz.read(filename))
        else:
            with codecs.open(path, 'r', 'utf-8') as fin:
                self.ProcessIOSData(fin.read())

    def ImportAndroidData(self, path):
        with open(path, 'r') as f:
            jsonobj = json.load(f)
            for item in jsonobj.get('favorite_table', []):
                volume = item.get('volume_column', 0)
                page = item.get('page_column', 0)
                code = constants.ANDROID_CODE_TABLE.get(item.get('language_column', -1)) 
                note = item.get('note_column', '')

                self.WriteXmlNoteFile(volume, page, code, note)
        
    def ImportData(self):
        ret = 0
        dlg = wx.FileDialog(self._view, _('Choose import data'), constants.HOME, '', 
                            constants.ETZ_TYPE, wx.OPEN|wx.CHANGE_DIR)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:        
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            
            if path.split('.')[-1] == 'etz':                
                with zipfile.ZipFile(path, 'r') as fz:
                    if len(fz.namelist()) > 1:
                        self.ImportPCData(path)
                    else:
                        self.ImportIOSData(path)
            elif path.split('.')[-1] == 'json':
                self.ImportIOSData(path)
            elif path.split('.')[-1] == 'js':
                self.ImportAndroidData(path)

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
            h = search.model.Model.GetHistories(self._view.TopBar.LanguagesComboBox.GetSelection(), 
                self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())[self._view.HistoryList.GetSelection()]
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
        
    def ShowInputText(self, text):
        self._view.SetPage('<div align="center"><h1>' + _('Search') + ': ' + text + '</h1></div>' if len(text) > 0 else '')

    def SaveSearches(self):
        self._view.SearchCtrl.SaveSearches()

    def ShowBookmarkPopup(self, x, y):
        self._view.ShowBookmarkPopup(x,y)
        
    def ShowNotesManager(self):        
        dlg = NoteManagerDialog(self._view)
        if dlg.ShowModal() == wx.ID_OK:
            volume, page, code = dlg.Result
            self.OpenBook(volume, page, code)
        dlg.Destroy()

    def SaveBookmark(self):        
        self._bookmarkManager.Save()        
        
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

    def OpenEnglishDict(self):

        def OnDictClose(event):
            self._englishDictWindow = None
            event.Skip()

        if self._englishDictWindow is None:
            self._englishDictWindow = widgets.EnglishDictWindow(self._view)
            self._englishDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._englishDictWindow.SetTitle(u'Pali-English Dictionary')

        self._englishDictWindow.Show()        
        self._englishDictWindow.Raise()        

    def SearchingBuddhawaj(self):
        return self._searchingBuddhawaj

    def TakeNote(self, code, volume, page, idx):
        note, state = self._model.GetNote(idx)
        dialog = NoteDialog(self._view, note, state)
        dialog.Center()
        if dialog.ShowModal() == wx.ID_OK:
            self._model.TakeNote(idx, dialog.GetNote(), dialog.GetState(), code)
        dialog.Destroy()

    def OpenSearchAndCompareDialog(self):

        def OnClose(event):
            self._searchAndCompareWindow = None
            event.Skip()

        if self._searchAndCompareWindow is None:
            self._searchAndCompareWindow = widgets.SearchAndCompareWindow(self._view.GetMDIParentFrame())
            self._searchAndCompareWindow.Delegate = self
            self._searchAndCompareWindow.Bind(wx.EVT_CLOSE, OnClose)
            self._searchAndCompareWindow.SetTitle(u'ค้นหาพร้อมจับคู่เลขข้อ')

        self._searchAndCompareWindow.Show()
        self._searchAndCompareWindow.Raise()

    def OnSearchAndCompareItemClick(self, code1, volume1, page1, keywords, code2, volume2, page2):
        self._delegate.ReadAndCompare(code1, volume1, page1, None, True, False, True, keywords, code2, volume2, page2)

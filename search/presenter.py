#-*- coding:utf-8 -*-

import search.model
from dialogs import AboutDialog, UpdateDialog, NoteManagerDialog, SimpleFontDialog, NoteDialog, MarkManagerDialog
import wx, zipfile, os, json, tempfile, sys, traceback
import xml.etree.ElementTree as ET
import wx.richtext as rt
from utils import BookmarkManager
import i18n
_ = i18n.language.ugettext

import constants, utils, threads, dialogs

import pony.orm
from pony.orm import db_session
import sqlite3

from packaging.version import Version
import settings, widgets

import read.model
import read.interactor
import read.view
import read.presenter

import codecs

def BuildBackupZip(out_path):
    """Write a .etz zip of constants.DATA_PATH to `out_path`. No UI."""
    rootlen = len(constants.DATA_PATH) + 1
    with zipfile.ZipFile(out_path, 'w') as fz:
        for base, dirs, files in os.walk(constants.DATA_PATH):
            for filename in files:
                fn = os.path.join(base, filename)
                fz.write(fn, fn[rootlen:])


def ImportSearchAndCompareHistory(src_db_path, dst_db_path):
    """Copy SearchAndCompareHistory + SearchAndCompareHistoryReadItem from
    `src_db_path` to `dst_db_path`.

    Dedupes SearchAndCompareHistory rows by the natural key
    (keywords1, keywords2, code1, code2). Old row IDs are remapped to the
    matching (existing or freshly-inserted) destination IDs so the FK on
    the items table remains valid. Items are deduped by
    (history, row, col)."""
    src = sqlite3.connect(src_db_path)
    dst = sqlite3.connect(dst_db_path)
    try:
        # Histories
        try:
            sch_rows = src.execute(
                'SELECT id, keywords1, keywords2, code1, code2, total, '
                'count1, count2 FROM SearchAndCompareHistory'
            ).fetchall()
        except sqlite3.Error:
            sch_rows = []

        id_map = {}
        for old_id, k1, k2, c1, c2, total, cnt1, cnt2 in sch_rows:
            found = dst.execute(
                'SELECT id FROM SearchAndCompareHistory '
                'WHERE keywords1=? AND keywords2=? AND code1=? AND code2=?',
                (k1, k2, c1, c2)
            ).fetchone()
            if found:
                id_map[old_id] = found[0]
            else:
                cur = dst.execute(
                    'INSERT INTO SearchAndCompareHistory '
                    '(keywords1, keywords2, code1, code2, total, count1, count2) '
                    'VALUES (?,?,?,?,?,?,?)',
                    (k1, k2, c1, c2, total, cnt1, cnt2)
                )
                id_map[old_id] = cur.lastrowid

        # Read items
        try:
            item_rows = src.execute(
                'SELECT history, row, col FROM SearchAndCompareHistoryReadItem'
            ).fetchall()
        except sqlite3.Error:
            item_rows = []

        for old_hist, row, col in item_rows:
            new_hist = id_map.get(old_hist)
            if new_hist is None:
                continue  # orphan — referenced history not in src
            dup = dst.execute(
                'SELECT 1 FROM SearchAndCompareHistoryReadItem '
                'WHERE history=? AND row=? AND col=?',
                (new_hist, row, col)
            ).fetchone()
            if dup:
                continue
            dst.execute(
                'INSERT INTO SearchAndCompareHistoryReadItem '
                '(history, row, col) VALUES (?,?,?)',
                (new_hist, row, col)
            )
        dst.commit()
    finally:
        src.close()
        dst.close()


DEFAULT_IOS_HIGHLIGHT_PALETTE = [
    '#B982CB', '#8C38BD', '#2DF487', '#99C860', '#DDEE0E',
    '#FDE0D2', '#B5E0F4', '#E78EC2', '#DD28BD', '#A52A33',
    '#B982CB', '#8C38BD', '#2DF487', '#99C860', '#DDEE0E',
]


def ResolveIOSHighlightColor(color_int, palette):
    """Map an iOS Highlight.color int (1..15) to a PC mark color string.

    `palette` is the list of dicts emitted under `highlightColors` in iOS's
    JSON v3 export — each row has `name` plus `highlight1`..`highlight15`
    columns of hex strings. We use the first row (iOS's default palette);
    a blank or missing entry falls back to the hard-coded iOS defaults.
    Color 0 (iOS 'unset') and out-of-range indices fall back to 'yellow'.
    """
    if not (1 <= color_int <= 15):
        return 'yellow'
    key = 'highlight%d' % color_int
    if palette:
        val = (palette[0] or {}).get(key, '')
        if val:
            return val
    return DEFAULT_IOS_HIGHLIGHT_PALETTE[color_int - 1]


def AppendPCMark(marks_root, code, volume, page, start, end, color):
    """Append a single PC mark to marks/<code>/<volume>-<page>.json.

    The PC mark format is a list of [marked, start, end, color] tuples
    (see read.presenter._LoadMarks). We dedupe by (start, end) to make
    re-imports idempotent — a re-import never duplicates a range, but a
    different color for an already-present range is also ignored (first
    write wins)."""
    code_dir = os.path.join(marks_root, code)
    if not os.path.exists(code_dir):
        os.makedirs(code_dir)
    path = os.path.join(code_dir, '%02d-%04d.json' % (volume, page))
    existing = []
    if os.path.exists(path):
        try:
            with open(path) as f:
                existing = json.load(f)
        except (ValueError, OSError):
            existing = []
    for entry in existing:
        if len(entry) >= 3 and entry[1] == start and entry[2] == end:
            return  # dedupe
    existing.append([True, start, end, color])
    with open(path, 'w') as f:
        json.dump(existing, f)


def ImportFavorites(src_db_path, dst_db_path):
    """Merge every bookmark table from `src_db_path` (fav.sqlite) into
    `dst_db_path`. Tables missing in the destination are created from the
    source's CREATE statement. Each row is deduped by all four columns
    (note, volume, page, parent_id) using IS-comparison so NULLs match."""
    src = sqlite3.connect(src_db_path)
    dst = sqlite3.connect(dst_db_path)
    try:
        tables = src.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for name, ddl in tables:
            if ddl:
                # Ensure the table exists in the destination. The source DDL
                # is `CREATE TABLE name (...)`; rewrite to IF NOT EXISTS so
                # we don't clobber an existing dst table.
                ddl_safe = ddl.replace(
                    'CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1)
                try:
                    dst.execute(ddl_safe)
                except sqlite3.Error:
                    pass

            qname = '"%s"' % name.replace('"', '""')
            rows = src.execute(
                'SELECT note, volume, page, parent_id FROM %s' % qname
            ).fetchall()
            for note, vol, page, pid in rows:
                # `IS` matches NULL == NULL (= behaves as false for NULL).
                dup = dst.execute(
                    'SELECT 1 FROM %s WHERE note IS ? AND volume IS ? '
                    'AND page IS ? AND parent_id IS ?' % qname,
                    (note, vol, page, pid)
                ).fetchone()
                if dup:
                    continue
                dst.execute(
                    'INSERT INTO %s (note, volume, page, parent_id) '
                    'VALUES (?,?,?,?)' % qname,
                    (note, vol, page, pid)
                )
        dst.commit()
    finally:
        src.close()
        dst.close()

class Presenter(object):
    def __init__(self, model, view, interactor):
        rt.RichTextBuffer.AddHandler(rt.RichTextXMLHandler())
        self._presenters = {}
        self._models = { 0:model }
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
        utils.UpdateDatabases()
         
    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, value):
        self._delegate = value
                
    @property
    def Model(self):
        return self._model
        
    @property
    def CanBeClosed(self):
        return self._canBeClosed
    
    @property
    def Code(self):
        return self.Model.Code

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
        
    def SetFocus(self):
        self._view.SearchCtrl.SetFocus()

    def Search(self, keywords=None, code=None, refreshHistoryList=True):
        self._refreshHistoryList = refreshHistoryList
        if not keywords:
            keywords = self._view.SearchCtrl.GetValue()

        if len(keywords.strip()) == 0 or len(keywords.replace('+',' ').strip()) == 0:
            return True
        
        position = constants.VISIBLE_LANGS_ORDER.index(constants.CODES.index(code)) if code is not None else 0
        if code is not None and position != self._view.TopBar.LanguagesComboBox.GetSelection():
            self._view.TopBar.LanguagesComboBox.SetSelection(position)
            self.SelectLanguage(position)
        
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
        if index not in self._models:        
            self._models[index] = search.model.SearchModelCreator.Create(self, index)
        
        self._model = self._models[index]

        self._view.VolumesRadio.Enable() if self._model.HasVolumeSelection() else self._view.VolumesRadio.Disable()

        self._view.BuddhawajOnly.Enable() if self._model.HasBuddhawaj() else self._view.BuddhawajOnly.Disable()
        self.RefreshHistoryList(index, self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())
        self._bookmarkManager = BookmarkManager(self._view, self._model.Code)

        self._view.SearchCtrl.SetValue(self._model.Keywords)
        self._view.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
        self._view.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))

        self._model.ReloadDisplay()

    def SelectTheme(self, index):
        utils.SaveTheme(index, constants.SEARCH)
        utils.ApplyTheme(self._view, constants.SEARCH)
        self._view.ResultsWindow.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
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
        self._view.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
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
        dlg = wx.FileDialog(self._view, _('Save data'), constants.HOME, zipFile, constants.ETZ_TYPE, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        dlg.Center()
        if dlg.ShowModal() == wx.ID_OK:
            BuildBackupZip(os.path.join(dlg.GetDirectory(), dlg.GetFilename()))
            wx.MessageBox(_('Export data complete'), 'E-Tipitaka')
        dlg.Destroy()

    def OpenAccount(self):
        from account.client import AccountClient
        from account.dialogs import AccountDialog
        from account.tokenstore import TokenStore
        store = TokenStore()
        client = AccountClient(constants.ACCOUNT_BASE_URL, store)
        dlg = AccountDialog(self._view, client, store, self)
        dlg.ShowModal()
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
        
        temp_data_sqlite = os.path.join(tempfile.gettempdir(), 'data.sqlite')
        if os.path.exists(temp_data_sqlite):
            conn = sqlite3.connect(temp_data_sqlite)
            cursor = conn.cursor()
            cursor.execute('PRAGMA user_version=4')
            cursor.execute('SELECT * FROM History')
            for col in cursor.fetchall():
                if len(col) == 7:
                    pk, keywords, total, code, read, skimmed, pages = col
                    notes = ''
                elif len(col) == 8:
                    pk, keywords, total, code, read, skimmed, pages, notes = col
                self.ImportHistory(keywords, total, code, read, skimmed, pages, notes)
            conn.commit()
            conn.close()
            # Search-and-compare history was added after the original import
            # path was written; merge it into the local data.sqlite too.
            ImportSearchAndCompareHistory(temp_data_sqlite, constants.DATA_DB)

        # fav.sqlite carries the bookmark tables (one per platform); merge
        # them row-by-row so a re-import after edits doesn't duplicate.
        temp_fav_sqlite = os.path.join(tempfile.gettempdir(), 'fav.sqlite')
        if os.path.exists(temp_fav_sqlite):
            try:
                ImportFavorites(temp_fav_sqlite, constants.FAV_DB)
            except Exception:
                traceback.print_exc()
            try:
                os.remove(temp_fav_sqlite)
            except OSError:
                pass

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

        original_text = ''
        for para in para_layout:
            for text in para:
                original_text += text.text
            original_text += '\n'

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

            if code is None or not constants.IS_CODE_ENABLED(code):
                continue
            self.WriteXmlNoteFile(volume, page, code, note)

        # iOS highlights map onto PC marks (filesystem: marks/<code>/<vol>-<page>.json).
        # Per-highlight notes/selection/html are dropped — PC marks don't carry text.
        palette = jsonobj.get('highlightColors', [])
        for item in jsonobj.get('highlights', []):
            code = constants.IOS_CODE_TABLE.get(item.get('code', -1))
            if not code or not constants.IS_CODE_ENABLED(code):
                continue
            volume = item.get('volume', 0)
            page = item.get('page', 0)
            start = item.get('start', 0)
            end = item.get('end', 0)
            if volume == 0 or page == 0 or end <= start:
                continue
            color = ResolveIOSHighlightColor(item.get('color', 0), palette)
            try:
                AppendPCMark(constants.MARKS_PATH, code, volume, page,
                             start, end, color)
            except OSError:
                traceback.print_exc()

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
                            constants.ETZ_TYPE, wx.FD_OPEN|wx.FD_CHANGE_DIR)
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

            wx.MessageBox(_('Import data complete'), 'E-Tipitaka')
            self.RefreshHistoryList(self._view.TopBar.LanguagesComboBox.GetSelection(), self._view.SortingRadioBox.GetSelection()==0, self._view.FilterCtrl.GetValue())                    
        dlg.Destroy()

    def SetUserDataDir(self):
        data = { 'copy': False , 'path': constants.DATA_PATH }
        dlg = dialogs.SettingUserDataDirDialog(self._view, data)
        
        if dlg.ShowModal() == wx.ID_OK:
            if data.get('path') != None and constants.DATA_PATH != data.get('path'):
                self.ChangeUserDataDir(constants.DATA_PATH, data.get('path'), data.get('copy', False))
        dlg.Destroy()

    def ChangeUserDataDir(self, oldpath, newpath, copy):
        import shutil
        
        def recursive_overwrite(src, dest, ignore=None):
            if os.path.isdir(src):
                if not os.path.isdir(dest):
                    os.makedirs(dest)
                files = os.listdir(src)
                if ignore is not None:
                    ignored = ignore(src, files)
                else:
                    ignored = set()
                for f in files:
                    if f not in ignored:
                        recursive_overwrite(os.path.join(src, f), 
                                            os.path.join(dest, f), 
                                            ignore)
            else:
                shutil.copyfile(src, dest)

        if copy:
            recursive_overwrite(oldpath, newpath)

        utils.SaveUserDataDir(newpath)
        wx.MessageBox('โปรแกรมจะปิดตัวเพื่อตั้งค่าใหม่ กรุณาเปิดโปรแกรมใหม่อีกครั้ง', 'การตั้งค่าใหม่สำเร็จแล้ว', wx.OK | wx.ICON_INFORMATION)
        sys.exit(0)
        
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

        if skipped == version or Version(version) <= Version(settings.VERSION): return
        
        dlg = UpdateDialog(self._view, settings.VERSION, version)
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            self.Download()
        elif ret == wx.ID_NO:
            self.SkipThisVersion(version)
        dlg.Destroy()
                
    def CheckNewUpdate(self):
        # Store builds: the Store handles app updates and forbids in-app
        # exe self-update. Suppress the version check / download prompt.
        if constants.IS_STORE_BUILD:
            return
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
        
    def LoadBookmarks(self, menu):

        def OnBookmark(event):
            item = self._view.GetBookmarkMenuItem(event.GetId())
            text = utils.ThaiToArabic(item.GetText())
            tokens = text.split(' ')
            volume, page = int(tokens[1]), int(tokens[3])            
            self.OpenBook(volume, page)

        self._bookmarkManager.MakeMenu(menu, OnBookmark)
        
    def OpenPaliDict(self):

        def OnDictClose(event):
            self._paliDictWindow = None
            event.Skip()

        if self._paliDictWindow is None:
            self._paliDictWindow = widgets.PaliDictWindow(self._view)
            self._paliDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._paliDictWindow.SetTitle('พจนานุกรม บาลี-ไทย')

        self._paliDictWindow.Show()        
        self._paliDictWindow.Raise()

    def OpenThaiDict(self):

        def OnDictClose(event):
            self._thaiDictWindow = None
            event.Skip()

        if self._thaiDictWindow is None:
            self._thaiDictWindow = widgets.ThaiDictWindow(self._view)
            self._thaiDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._thaiDictWindow.SetTitle('พจนานุกรม ภาษาไทย ฉบับราชบัณฑิตยสถาน')

        self._thaiDictWindow.Show()        
        self._thaiDictWindow.Raise()

    def OpenEnglishDict(self):

        def OnDictClose(event):
            self._englishDictWindow = None
            event.Skip()

        if self._englishDictWindow is None:
            self._englishDictWindow = widgets.EnglishDictWindow(self._view)
            self._englishDictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._englishDictWindow.SetTitle('Pali-English Dictionary')

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
            self._searchAndCompareWindow.SetTitle('ค้นหาพร้อมจับคู่เลขข้อ')

        self._searchAndCompareWindow.Show()
        self._searchAndCompareWindow.Raise()

    def OnSearchAndCompareItemClick(self, code1, volume1, page1, keywords, code2, volume2, page2, keywords2):
        self._delegate.ReadAndCompare(code1, volume1, page1, None, True, False, True, keywords, code2, volume2, page2, keywords2)

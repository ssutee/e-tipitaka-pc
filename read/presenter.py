#-*- coding:utf-8 -*-

import wx
import wx.richtext as rt
from wx.html import HtmlEasyPrinting
import constants, utils, dialogs, widgets
import os, json, codecs

from pony.orm import Database, Required, Optional, db_session, select, desc

from read.model import Model

class Printer(HtmlEasyPrinting):
    def __init__(self):
        HtmlEasyPrinting.__init__(self)
    
    def GetHtmlText(self, text):
        return text
        
    def Print(self, text, doc_name):
        self.SetHeader(doc_name)
        self.PrintText(self.GetHtmlText(text), doc_name)
        
    def PreviewText(self, text, doc_name):
        self.SetHeader(doc_name)
        HtmlEasyPrinting.PreviewText(self, self.GetHtmlText(text))

class KeyCommandHandler(object):
    def __init__(self):
        self._command = ''
        self._filter = {3653:49, 47:50, 45:51, 3616:52, 3606:53, 3640:54, 3638:55, 3588:56, 3605:57, 3592:48, 3651:46}
        
    def Handle(self, event, code):
        code = self._filter.get(code, code)        
        if ((event.CmdDown() or event.ControlDown()) and code == 102) or code == 6:
            self._command = ''
            return constants.CMD_FIND
        elif code == wx.WXK_LEFT:
            self._command = ''
            return constants.CMD_BACKWARD
        elif code == wx.WXK_RIGHT:
            self._command = ''
            return constants.CMD_FORWARD
        elif (code >= 48 and code <= 57) or code == 46:
            self._command += chr(code)
            return constants.CMD_IDLE
        elif code == 105 or code == 112 or code == 118 or code == 3618 or code == 3619 or code == 3629:
            self._result = self._command
            self._command = ''                
            if code == 3619 or code == 105:
                return constants.CMD_JUMP_TO_ITEM
            elif code == 3618 or code == 112:
                return constants.CMD_JUMP_TO_PAGE
            elif code == 3629 or code == 118:
                return constants.CMD_JUMP_TO_VOLUME
            return constants.CMD_IDLE            
        elif code == 43:
            self._command = ''
            return constants.CMD_ZOOM_IN
        elif code == 45:
            self._command = ''
            return constants.CMD_ZOOM_OUT

        self._command = ''                
        return constants.CMD_IDLE
        
    @property
    def Result(self):
        return self._result
        
class FindTextHandler(object):
    def __init__(self):
        self._direction = constants.DOWN
        self._text = ''
        self.Reset()        
        
    def Reset(self):
        self._content = None
        self._position = 0
        
    @property
    def Text(self):
        return self._text
        
    @property
    def Direction(self):
        return self._direction
        
    def Handle(self, text, content, direction):
        if content != self._content:
            self._content = content
            self._position = 0
        elif self._direction != direction:
            self._position += len(self._text) if direction == constants.DOWN else -len(self._text)
            
        self._direction = direction
        self._text = text
                        
        n = -1
        while True:            
            start = 0 if direction == constants.UP else self._position
            end = self._position if direction == constants.UP else len(content) + 1
            n = getattr(content, 'rfind' if direction == constants.UP else 'find')(self._text, start, end)
            if n == -1: break
            self._position = n + (0 if direction == constants.UP else len(self._text))
            return n, self._position != 0

        return n, self._position != 0
        
class BookmarkManager(object):
    def __init__(self, view, code):
        self._items = []
        self._view = view
        self._code = code
        self.Load()
                
    def Load(self):
        filename = os.path.join(constants.BOOKMARKS_PATH,'%s.fav'%(self._code))
        if not os.path.exists(filename): return
        self._items = []
        roots = [self._items]
        with codecs.open(filename,'r','utf8') as f:
            for text in f:
                if text.strip() == '': continue
                n_root = text.rstrip().count(u'\t')
                if n_root > len(roots): continue
                root = roots[n_root]
                if text.strip()[0] == '~':
                    child = []
                    root.append({text.strip().strip(u'~') : child})
                    try:
                        roots[n_root+1] = child
                    except IndexError,e:
                        roots.append(child)
                else:
                    tokens = utils.ArabicToThai(text.strip()).split()
                    root.append((int(tokens[1]), int(tokens[3]), text.strip()))
        map(lambda x:x.sort(), roots)
        
    def Save(self):
        
        def _Save(items, out, depth=0):
            for item in items:
                if isinstance(item, dict):
                    folder = item.keys()[0]
                    out.write(u'\t'*depth + '~' + folder + '\n')
                    _Save(item[folder], out, depth+1)
                elif isinstance(item, tuple):
                    out.write(u'\t'*depth + item[2] + '\n')

        if not os.path.exists(constants.BOOKMARKS_PATH):
            os.makedirs(constants.BOOKMARKS_PATH)
        
        with codecs.open(os.path.join(constants.BOOKMARKS_PATH,'%s.fav'%(self._code)),'w','utf8') as out:
            _Save(self._items, out)

        
    def MakeMenu(self, menu, handler):
        def _MakeMenu(root, items):
            for item in items:
                if isinstance(item, dict):
                    child = wx.Menu()
                    folder = item.keys()[0]
                    _MakeMenu(child, item[folder])
                    root.AppendMenu(-1, folder, child)
                elif isinstance(item, tuple):
                    menuItem = root.Append(-1, item[2])
                    menuItem.volume = item[0]
                    menuItem.page = item[1]
                    self._view.Bind(wx.EVT_MENU, handler, menuItem)
        _MakeMenu(menu, self._items)
        
    @property
    def Items(self):
        return self._items

class Presenter(object):
    def __init__(self, model, view, interactor, code):
        self._stopOpen = False
        self._currentPage = 0
        self._currentVolume = 0
        self._code = code
        self._keywords = None
        self._comparePage = {}
        self._compareVolume = {}
        
        self._saveDirectory = constants.HOME        
        
        self._focusList = []
        self._lastFocus = None
        
        self._marks = {}

        self._model = model
        self._delegate = None
        self._view = view
        self._view.DataSource = self
        self._view.Delegate = self
        self._view.SetTitle(self._model.GetTitle())
        self._view.Start()
        interactor.Install(self, view)     
        
        self._keyCommandHandler = KeyCommandHandler()
        self._findTextHandler = FindTextHandler()
        self._bookmarkManager = BookmarkManager(self._view, code)
        
        rt.RichTextBuffer.AddHandler(rt.RichTextXMLHandler())

        self._SetupPrinter()
        
        self._dictWindow = None

    @property
    def CurrentVolume(self):
        return self._currentVolume
        
    @property
    def CurrentPage(self):
        return self._currentPage
        
    @property
    def BookmarkItems(self):
        return self._bookmarkManager.Items

    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate
        
    @property
    def Keywords(self):
        return self._keywords
        
    @Keywords.setter
    def Keywords(self, keywords):
        self._keywords = keywords

    def _SetupPrinter(self):
        self._printer = Printer()
        data = self._printer.GetPageSetupData()
        data.SetDefaultMinMargins(False)
        data.SetMarginTopLeft((20,20))
        data.SetMarginBottomRight((10,10))        

    def BringToFront(self):
        self._view.Raise()
        self._view.Iconize(False)

    def _LoadNoteText(self, volume, page):
        self._view.NoteTextCtrl.SelectAll()
        self._view.NoteTextCtrl.DeleteSelection()        
        self._view.NoteTextCtrl.EndAllStyles()
        path = os.path.join(constants.NOTES_PATH, self._model.Code)
        if not os.path.exists(path):
            os.makedirs(path)  
        filename = os.path.join(path, '%02d-%04d.xml'%(volume, page))
        self._view.NoteTextCtrl.SetFilename(filename)
        if os.path.exists(filename):
            self._view.NoteTextCtrl.LoadFile(filename, rt.RICHTEXT_TYPE_XML)        
        self._view.NoteTextCtrl.SetModified(False)

    def _MarkKey(self, code, volume, page):
        code = self._model.Code if code is None else code
        return '%s-%02d-%04d' % (code, volume, page)

    def _LoadMarks(self, volume, page, code=None):
        path = os.path.join(constants.MARKS_PATH, self._model.Code if code is None else code)
        if not os.path.exists(path):
            os.makedirs(path)        

        filename = os.path.join(path, '%02d-%04d.json'%(volume, page))
        key = self._MarkKey(code, volume, page)
        if os.path.exists(filename):
            with open(filename) as f: self._marks[key] = json.load(f)
        else:
            self._marks[key] = []
                
        for marked, s, t in self._marks[key]:
            self._view.MarkText(code, (s,t)) if marked else self._view.UnmarkText(code, (s,t))                

    def OpenBook(self, volume, page, section=None, selectItem=False):
        self._findTextHandler.Reset()

        page = self._model.GetFirstPageNumber(volume) if page < self._model.GetFirstPageNumber(volume) else page

        if page > self._model.GetTotalPages(volume) or page < self._model.GetFirstPageNumber(volume): return

        self._currentVolume = volume
        self._currentPage = page

        self._LoadNoteText(self._currentVolume, self._currentPage)

        self._ToggleCompareComboBox(self._currentVolume)
        self._ToggleNavigationButtons(self._currentVolume)

        self._view.SetTitles(*self._model.GetTitles(self._currentVolume, section))
        self._view.SetPageNumber(self._currentPage if self._currentPage > 0 else None)
        self._view.SetItemNumber(*self._model.GetItems(self._currentVolume, self._currentPage))        
        self._view.UpdateSlider(self._currentPage, self._model.GetFirstPageNumber(self._currentVolume), 
            self._model.GetTotalPages(self._currentVolume))

        content = self._model.GetPage(self._currentVolume, self._currentPage)
        
        # work around for fixing font size problem on win32
        self._view.SetText(content)        
        self._view.SetText(content)
        self._view.StatusBar.SetStatusText(u'', 0)
        self._view.StatusBar.SetStatusText(u'คำค้นหาคือ "%s"'%(self._keywords) if self._keywords is not None and len(self._keywords) > 0 else u'', 1)

        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))

        self._HighlightKeywords(content, self._keywords)        
        self._LoadMarks(self._currentVolume, self._currentPage)
        
        if hasattr(self._delegate, 'OnReadWindowOpenPage'):
            self._delegate.OnReadWindowOpenPage(self._currentVolume, self._currentPage, self._code)

        self._stopOpen = True
        if selectItem: self._view.SetBookListSelection(self._currentVolume)        
        self._stopOpen = False

    def OpenAnotherBook(self, code, volume, page):
        self._findTextHandler.Reset()        
        currentCode = self._model.Code
        self._model.Code = code

        if page > self._model.GetTotalPages(volume) or page < self._model.GetFirstPageNumber(volume): return

        self._compareVolume[code] = volume        
        self._comparePage[code] = page
                
        self._ToggleNavigationButtons(self._compareVolume[code], code)
                
        self._view.SetTitles(*self._model.GetTitles(volume, None), code=code)        
        self._view.SetPageNumber(page if page > 0 else None, code=code)
        self._view.SetItemNumber(*self._model.GetItems(volume, page), code=code)
        self._view.UpdateSlider(page, self._model.GetFirstPageNumber(volume), self._model.GetTotalPages(volume), code)        
        
        content = self._model.GetPage(volume, page)
        self._view.SetText(content, code=code)       
        self._view.FormatText(self._model.GetFormatter(volume, page), code=code)        
        self._LoadMarks(volume, page, code)        

        self._model.Code = currentCode                

    def _HighlightKeywords(self, content, keywords):
        if content == u'' or keywords is None: return

        font = self._view.Body.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        for term in keywords.replace('+',' ').replace('|',' ').split():
            n = -1
            while True:                    
                n = content.find(self._model.ConvertSpecialCharacters(term), n+1)
                if n == -1: break                
                offset = self._model.HighlightOffset                
                self._view.Body.Freeze()
                self._view.Body.SetStyle(n-offset, n+len(term)-offset, wx.TextAttr('purple', wx.NullColour, font))
                self._view.Body.Thaw()

    def OnLinkToReference(self, code, volume, item):
        self._DoCompare(code, volume, 1, item)

    def SaveBookmark(self):
        self._bookmarkManager.Save()

    def Close(self):
        self._stopOpen = True
        self.SaveBookmark()
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def _DoForward(self, code=None):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage+1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], self._comparePage[code] + 1)

    def Forward(self):
        self._DoForward(self._lastFocus)
        
    def _DoBackward(self, code=None):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage-1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], self._comparePage[code] - 1)
                
    def Backward(self, code=None):
        self._DoBackward(self._lastFocus)

    def HandleBookSelection(self, event):
        if self._stopOpen: return
        
        if isinstance(event, wx.TreeEvent):
            volume, page, section = self._view.BookList.GetItemPyData(event.GetItem())
            self.OpenBook(volume, page, section if section is not None else self._model.GetSection(volume, page))
        elif isinstance(event, wx.CommandEvent):
            self.OpenBook(event.GetSelection()+1, self._model.GetFirstPageNumber(event.GetSelection()+1))
            
    def HandleTextSelection(self, text, code):
        text = text.strip().split('\n')[0]        
        self._view.StatusBar.SetStatusText(u'คำที่เลือกคือ "%s"' % text if len(text) > 0 else u'', 0)
        if self._dictWindow is not None:            
            self._dictWindow.SetInput(text)
            
    def JumpToPage(self, page, code=None):
        if code is None:
            page = page if page > 0 and page <= self._model.GetTotalPages(self._currentVolume) else self._model.GetFirstPageNumber(self._currentVolume)
            self.OpenBook(self._currentVolume, page, self._model.GetSection(self._currentVolume, page))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], page)
        
    def JumpToItem(self, item, code=None):
        page, sub = 0, 0

        try:
            if len(item.split('.')) == 2:
                item, sub = map(int, item.split('.'))
            elif len(item.split('.')) == 1:
                item, sub = int(item), 1
        except ValueError, e:
            pass

        try:
            currentCode = self._model.Code                
            self._model.Code = code if code is not None else currentCode
            page = self._model.ConvertItemToPage(self._currentVolume if code is None else self._compareVolume[code], item, sub, self._view.CheckBox.IsChecked())
            self._model.Code = currentCode
        except ValueError, e:
            pass
            
        self.JumpToPage(page, code)

    def CompareTo(self, index):
        item = None    
        items = self._model.GetItems(self._currentVolume, self._currentPage)
        if len(items) > 1:
            dialog = wx.SingleChoiceDialog(self._view, u'เลือกข้อที่ต้องการเทียบเคียง', 
                self._model.GetTitle(self._currentVolume), map(lambda x: u'ข้อที่ ' + utils.ArabicToThai(x), items))
            if dialog.ShowModal() == wx.ID_OK:
                item = items[dialog.GetSelection()]
            dialog.Destroy()
        elif len(items) == 1:
            item = items[0]

        item, sub = self._model.GetSubItem(self._currentVolume, self._currentPage, item)
        volume = self._model.GetComparingVolume(self._currentVolume, self._currentPage)

        self._DoCompare(constants.CODES[index], volume, sub, item)

    def _DoCompare(self, code, volume, sub, item):        
        if item is None: return
        
        self._view.HideBookList()
        self._view.AddReadPanel(code)
        currentCode = self._model.Code
        self._model.Code = code
        volume = self._model.ConvertVolume(volume, item, sub)
        page = self._model.ConvertItemToPage(volume, item, sub, code == constants.THAI_MAHACHULA_CODE)
        self._model.Code = currentCode
        self.OpenAnotherBook(code, volume, page)

    def SetFocus(self, flag, code):
        if flag and code is not None:
            self._focusList.append(code)
            self._lastFocus = code
        elif not flag and code is not None:
            self._focusList.remove(code)
        elif flag and code is None:
            self._focusList = []
            self._lastFocus = None                 
            
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        self._ToggleNavigationButtons(volume, self._lastFocus)
    
    def ProcessKeyCommand(self, event, keyCode, code):
        ret = self._keyCommandHandler.Handle(event, keyCode)        
        if ret == constants.CMD_FIND:
            self.Find(code)
        elif ret == constants.CMD_FORWARD:
            self._DoForward(code)
        elif ret == constants.CMD_BACKWARD:
            self._DoBackward(code)
        elif ret == constants.CMD_JUMP_TO_PAGE:
            self.JumpToPage(int(self._keyCommandHandler.Result), code)
        elif ret == constants.CMD_JUMP_TO_ITEM:
            self.JumpToItem(self._keyCommandHandler.Result, code)
        elif ret == constants.CMD_JUMP_TO_VOLUME:
            volume = int(self._keyCommandHandler.Result)
            self.OpenAnotherBook(code, volume, 1) if code is not None else self.OpenBook(volume, 1, selectItem=True)
        elif ret == constants.CMD_ZOOM_IN:
            self.IncreaseFontSize()
        elif ret == constants.CMD_ZOOM_OUT:
            self.DecreaseFontSize()
            
    def Find(self, code):
        self._view.ShowFindDialog(code, self._findTextHandler.Text, self._findTextHandler.Direction)
        
    def DoFind(self, code, text, content, flags):
        n, found = self._findTextHandler.Handle(text, content, flags)
        if n > -1:
            self._view.SetSelection(content, n, n+len(text), code)
        elif found:
            dlg = wx.MessageDialog(self._view, u'การค้นหาสิ้นสุดแล้ว', 'Find', style=wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            self._findTextHandler.Reset()
        else:
            dlg = wx.MessageDialog(self._view, u'ไม่พบคำที่ค้นหา', 'Find', style=wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            self._findTextHandler.Reset()            
            
    def ToggleBookList(self):
        self._view.ToggleBookList()
        
    def ShowFontDialog(self):
        code = self._lastFocus if self._lastFocus else self._model.Code
        curFont = utils.LoadFont(constants.READ_FONT, code)
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        if curFont != None:
            fontData.SetInitialFont(curFont)
        dialog = wx.FontDialog(self._view, fontData)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            if font.IsOk():
                utils.SaveFont(font, constants.READ_FONT, code)                
                self._view.SetFont(font, self._lastFocus)        
        dialog.Destroy()

    def IncreaseFontSize(self):
        code = self._lastFocus if self._lastFocus else self._model.Code
        font = utils.LoadFont(constants.READ_FONT, code)
        font.SetPointSize(font.GetPointSize()+1)
        utils.SaveFont(font, constants.READ_FONT, code)        
        self._view.SetFont(font, self._lastFocus)        
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        
    def DecreaseFontSize(self):
        code = self._lastFocus if self._lastFocus else self._model.Code
        font = utils.LoadFont(constants.READ_FONT, code)
        font.SetPointSize(font.GetPointSize()-1)
        utils.SaveFont(font, constants.READ_FONT, code)
        self._view.SetFont(font, self._lastFocus)
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        
    def MarkText(self, code, mark=True):
        s,t = self._view.MarkText(code) if mark else self._view.UnmarkText(code)
        volume = self._currentVolume if code is None else self._compareVolume[code]
        page = self._currentPage if code is None else self._comparePage[code]
        key = self._MarkKey(code, volume, page)
        if key not in self._marks:
            self._marks[key] = [(mark, s, t)]
        else:
            self._marks[key] += [(mark, s, t)]
        
    def UnmarkText(self, code):
        self.MarkText(code, False)
        
    def IndentLessNoteText(self):
        attr = rt.TextAttrEx()
        attr.SetFlags(rt.TEXT_ATTR_LEFT_INDENT)
        ip = self._view.NoteTextCtrl.GetInsertionPoint()
        if self._view.NoteTextCtrl.GetStyle(ip, attr):
            r = rt.RichTextRange(ip, ip)
            if self._view.NoteTextCtrl.HasSelection():
                r = self._view.NoteTextCtrl.GetSelectionRange()

        if attr.GetLeftIndent() >= 100:
            attr.SetLeftIndent(attr.GetLeftIndent() - 100)
            attr.SetFlags(rt.TEXT_ATTR_LEFT_INDENT)
            self._view.NoteTextCtrl.SetStyle(r, attr)
    
    def IndentMoreNoteText(self):
        attr = rt.TextAttrEx()
        attr.SetFlags(rt.TEXT_ATTR_LEFT_INDENT)
        ip = self._view.NoteTextCtrl.GetInsertionPoint()
        if self._view.NoteTextCtrl.GetStyle(ip, attr):
            r = rt.RichTextRange(ip, ip)
            if self._view.NoteTextCtrl.HasSelection():
                r = self._view.NoteTextCtrl.GetSelectionRange()

            attr.SetLeftIndent(attr.GetLeftIndent() + 100)
            attr.SetFlags(rt.TEXT_ATTR_LEFT_INDENT)
            self._view.NoteTextCtrl.SetStyle(r, attr)
            
    def ApplyFontToNoteText(self):
        if not self._view.NoteTextCtrl.HasSelection():
            return

        r = self._view.NoteTextCtrl.GetSelectionRange()
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        attr = rt.TextAttrEx()
        attr.SetFlags(rt.TEXT_ATTR_FONT)
        if self._view.NoteTextCtrl.GetStyle(self._view.NoteTextCtrl.GetInsertionPoint(), attr):
            fontData.SetInitialFont(attr.GetFont())

        dlg = wx.FontDialog(self._view, fontData)
        if dlg.ShowModal() == wx.ID_OK:
            fontData = dlg.GetFontData()
            font = fontData.GetChosenFont()
            if font:
                attr.SetFlags(rt.TEXT_ATTR_FONT)
                attr.SetFont(font)
                self._view.NoteTextCtrl.SetStyle(r, attr)
        dlg.Destroy()

    def ApplyFontColorToNoteText(self):
        colourData = wx.ColourData()
        attr = rt.TextAttrEx()
        attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)
        if self._view.NoteTextCtrl.GetStyle(self._view.NoteTextCtrl.GetInsertionPoint(), attr):
            colourData.SetColour(attr.GetTextColour())

        dlg = wx.ColourDialog(self._view, colourData)
        if dlg.ShowModal() == wx.ID_OK:
            colourData = dlg.GetColourData()
            colour = colourData.GetColour()
            if colour:
                if not self._view.NoteTextCtrl.HasSelection():
                    self._view.NoteTextCtrl.BeginTextColour(colour)
                else:
                    r = self._view.NoteTextCtrl.GetSelectionRange()
                    attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)
                    attr.SetTextColour(colour)
                    self._view.NoteTextCtrl.SetStyle(r, attr)
        dlg.Destroy()
        
    def _CurrentMarkKey(self, code):
        if code not in self._compareVolume or code not in self._comparePage: return None
        volume = self._currentVolume if code is None else self._compareVolume[code]
        page = self._currentPage if code is None else self._comparePage[code]
        return self._MarkKey(code, volume, page)
              
    def _CurrentMarkFilename(self, code):
        if code not in self._compareVolume or code not in self._comparePage: return None
        volume = self._currentVolume if code is None else self._compareVolume[code]
        page = self._currentPage if code is None else self._comparePage[code]        
        path = os.path.join(constants.MARKS_PATH, self._model.Code if code is None else code)        
        return os.path.join(path, '%02d-%04d.json'%(volume, page))        
    
    @db_session            
    def SaveNoteText(self):
        self._view.NoteTextCtrl.SaveFile(self._view.NoteTextCtrl.GetFilename(), rt.RICHTEXT_TYPE_XML)
        self._view.NoteTextCtrl.SetModified(False)
        note = Model.Note(volume=self._currentVolume, page=self._currentPage, code=self._model.Code, 
            text=self._view.NoteTextCtrl.GetValue(), filename=self._view.NoteTextCtrl.GetFilename())
                        
    def SaveMarkedText(self, code):
        key = self._CurrentMarkKey(code)                
        filename = self._CurrentMarkFilename(code)

        if filename is None or key is None: return
        
        if key not in self._marks or len(self._marks[key]) == 0: 
            os.remove(filename) if os.path.exists(filename) else None
        else:
            with open(filename, 'w') as f: json.dump(self._marks[key], f)
        
    def ClearMarkedText(self, code):
        dlg = wx.MessageDialog(self._view, u'คุณต้องการลบการระบายสีข้อความทั้งหมดหรือไม่?', u'ยืนยันการลบ', 
            wx.YES_NO|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self._marks[self._CurrentMarkKey(code)] = []
            self._view.ClearMarks(code)
            self.SaveMarkedText(code)
        dlg.Destroy()
        
    def HasSavedMark(self, code):        
        return os.path.exists(self._CurrentMarkFilename(code)) if self._CurrentMarkFilename(code) is not None else False
        
    def HasMarkText(self, code):
        return any(map(lambda x:x[0], self._marks.get(self._CurrentMarkKey(code), [])))
        
    def ShowBookmarkPopup(self, x, y):
        self._view.ShowBookmarkPopup(x,y)
        
    def ShowPrintDialog(self):
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        page = self._currentPage if self._lastFocus is None else self._comparePage[self._lastFocus]
        
        currentCode = self._model.Code
        self._model.Code = currentCode if self._lastFocus is None else self._lastFocus
        
        title1, title2 = self._model.GetTitles(volume)
        total = self._model.GetTotalPages(volume)

        data = {'from':page-1 if page > 0 else 0, 'to':page-1 if page > 0 else 0}
        dlg = dialogs.PageRangeDialog(self._view, u'โปรดเลือกหน้าที่ต้องการพิมพ์', title1, title2, total, data)
        
        if dlg.ShowModal() == wx.ID_OK:
            font = utils.LoadFont(constants.READ_FONT, self._model.Code)
            text = u'<font face="%s" size=+2>' % ('TF Chiangsaen' if font is None else font.GetFaceName())
            text += u"<div align=center><b>%s</b><br><b>%s</b><br><b>%s</b><br>หน้าที่ %s ถึง %s</div><hr>" % \
                (self._model.GetTitle(), title1, title2, 
                 utils.ArabicToThai(str(data['from']+1).decode('utf8','ignore')), 
                 utils.ArabicToThai(str(data['to']+1).decode('utf8','ignore')))
            
            for p in range(data['from'], data['to']+1) if data['from'] <= data['to'] else range(data['from'], data['to']-1, -1):
                content = self._model.GetPage(volume, p+1).replace(u'\t', u'&nbsp;'*7).replace(u'\x0a', u'<br>')
                content = content.replace(u'\x0b', u'<br>').replace(u'\x0c', u'<br>').replace(u'\x0d', u'<br>')
                text += u'<div align=right>หน้าที่ %s</div><p>'%(utils.ArabicToThai(str(p+1).decode('utf8','ignore')))
                text += u'%s<p><p><p>'%(content)
            text += u'</font>'
            self._printer.Print(text, "")

        dlg.Destroy()
    
        self._model.Code = currentCode

    def _ShowConfirmSaveDialog(self, code, volume, data, text):
        dlg = wx.FileDialog(self._view, u'โปรดเลือกไฟล์', self._saveDirectory, 
            '%s_volumn-%02d_page-%04d-%04d' % (code, volume, data['from']+1, data['to']+1), 
            u'Plain Text (*.txt)|*.txt', wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            with codecs.open(os.path.join(dlg.GetDirectory(), dlg.GetFilename()), 'w', 'utf-8') as f:
                f.write(text)
            self._saveDirectory = dlg.GetDirectory()                
        dlg.Destroy()
        
    def ShowSaveDialog(self):
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        page = self._currentPage if self._lastFocus is None else self._comparePage[self._lastFocus]
        
        currentCode = self._model.Code
        self._model.Code = currentCode if self._lastFocus is None else self._lastFocus
        
        title1, title2 = self._model.GetTitles(volume)
        total = self._model.GetTotalPages(volume)

        data = {'from':page-1 if page > 0 else 0, 'to':page-1 if page > 0 else 0}
        dlg = dialogs.PageRangeDialog(self._view, u'โปรดเลือกหน้าที่ต้องการบันทึก', title1, title2, total, data)        
        if dlg.ShowModal() == wx.ID_OK:
            text = u'%s\n%s\n\n' % (title1, title2)
            for p in range(data['from'], data['to']+1) if data['from'] <= data['to'] else range(data['from'], data['to']-1, -1):
                content = self._model.GetPage(volume, p+1)
                text += u' '*60 + u'หน้าที่ %s\n\n'%(utils.ArabicToThai(str(page+1).decode('utf8','ignore')))
                text += u'%s\n\n\n' % (content)
            self._ShowConfirmSaveDialog(self._model.Code, volume, data, text)
        dlg.Destroy()
    
        self._model.Code = currentCode        
        
    def LoadBookmarks(self, menu):
        
        def OnBookmark(event):
            item = self._view.GetBookmarkMenuItem(event.GetId())
            text = utils.ThaiToArabic(item.GetText())
            tokens = text.split(' ')
            volume, page = int(tokens[1]), int(tokens[3])            
            self.OpenBook(volume, page, selectItem=True)
        
        self._bookmarkManager.MakeMenu(menu, OnBookmark)
        
    def SearchSelection(self, selection=None):
        code = self._lastFocus
        keywords = self._view.GetStringSelection(code) if selection is None else selection
        
        if len(keywords.strip()) == 0: return

        self.Delegate.BringToFront()
        self.Delegate.Search(utils.ConvertToThaiSearch(keywords), code if code is not None else self._model.Code)

    def OpenDict(self):
        
        def OnDictClose(event):
            self._dictWindow = None
            event.Skip()
        
        if self._dictWindow is None:
            self._dictWindow = widgets.DictWindow(self._view)
            self._dictWindow.Bind(wx.EVT_CLOSE, OnDictClose)
            self._dictWindow.SetTitle(u'พจนานุกรม บาลี-ไทย')
            
        self._dictWindow.Show()        
        text = self._view.GetStringSelection(self._lastFocus)
        self._dictWindow.SetInput(text.strip().split('\n')[0].strip())
        
    def ShowContextMenu(self, window, position, code):
        self._view.ShowContextMenu(window, position, code)
        
    def ShowNotesManager(self):
        if self._dictWindow is not None:
            self._dictWindow.Close()
            self._dictWindow = None
            
        dlg = dialogs.NoteManagerDialog(self._view, self._model.Code)
        if dlg.ShowModal() == wx.ID_OK:
            volume, page = dlg.Result
            self.OpenBook(volume, page)
        dlg.Destroy()

    def _ToggleCompareComboBox(self, volume):
        getattr(self._view.CompareComboBox, 'Disable' if self._currentPage == 0 else 'Enable')()
    
    def _ToggleNavigationButtons(self, volume, code=None):
        if code == None:
            getattr(self._view.BackwardButton, 'Disable' if self._currentPage <= self._model.GetFirstPageNumber(volume) else 'Enable')()
            getattr(self._view.ForwardButton, 'Disable' if self._currentPage >= self._model.GetTotalPages(volume) else 'Enable')()
        else:
            currentCode = self._model.Code
            self._model.Code = code
            getattr(self._view.BackwardButton, 'Disable' if self._comparePage[code] <= self._model.GetFirstPageNumber(volume) else 'Enable')()
            getattr(self._view.ForwardButton, 'Disable' if self._comparePage[code] >= self._model.GetTotalPages(volume) else 'Enable')()            
            self._model.Code = currentCode

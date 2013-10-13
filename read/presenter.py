#-*- coding:utf-8 -*-

import wx
import wx.richtext as rt
import constants, utils
import os, json, codecs

class KeyCommandHandler(object):
    def __init__(self):
        self._command = ''
        self._filter = {3653:49, 47:50, 45:51, 3616:52, 3606:53, 3640:54, 3638:55, 3588:56, 3605:57, 3592:48, 3651:46}
        
    def Handle(self, event, code):
        code = self._filter.get(code, code)        
        if (event.CmdDown() or event.ControlDown()) and code == 102:
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
            self._position = len(content) if direction == constants.UP else 0            
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
            return n
    
        return n
        
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
        self._code = code
        self._keywords = None
        self._model = model
        self._delegate = None
        self._view = view
        self._view.DataSource = self
        self._view.Delegate = self
        self._view.SetTitle(self._model.GetTitle())
        self._view.Start()
        interactor.Install(self, view)     
        self._currentPage = 0
        self._currentVolume = 0

        self._comparePage = {}
        self._compareVolume = {}
        
        self._focusList = []
        self._marks = {}
        
        self._keyCommandHandler = KeyCommandHandler()
        self._findTextHandler = FindTextHandler()
        self._bookmarkManager = BookmarkManager(self._view, code)
        
        
        rt.RichTextBuffer.AddHandler(rt.RichTextXMLHandler())

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

    def BringToFront(self):
        self._view.Raise()
        self._view.Iconize(False)

    def _LoadNoteText(self, volume, page):
        self._view.NoteTextCtrl.SelectAll()
        self._view.NoteTextCtrl.DeleteSelection()        
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

        self._ToggleButtons(self._currentVolume)

        self._view.SetTitles(*self._model.GetTitles(self._currentVolume, section))
        self._view.SetPageNumber(self._currentPage if self._currentPage > 0 else None)
        self._view.SetItemNumber(*self._model.GetItems(self._currentVolume, self._currentPage))        

        content = self._model.GetPage(self._currentVolume, self._currentPage)
        self._view.SetText(content)
        self._HighlightKeywords(content, self._keywords)
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        self._LoadMarks(self._currentVolume, self._currentPage)
        self._view.UpdateSlider(self._currentPage, self._model.GetFirstPageNumber(self._currentVolume), 
            self._model.GetTotalPages(self._currentVolume))
        
        if selectItem:
            self._view.SetBookListSelection(self._currentVolume)        
        
        if hasattr(self._delegate, 'OnReadWindowOpenPage'):
            self._delegate.OnReadWindowOpenPage(volume, page, self._code)
            
    def OpenAnotherBook(self, code, volume, page):
        self._findTextHandler.Reset()        
        currentCode = self._model.Code
        self._model.Code = code

        if page > self._model.GetTotalPages(volume) or page < self._model.GetFirstPageNumber(volume): return

        self._compareVolume[code] = volume        
        self._comparePage[code] = page
                
        self._view.SetTitles(*self._model.GetTitles(volume, None), code=code)        
        self._view.SetPageNumber(self._comparePage[code] if self._comparePage[code] > 0 else None, code=code)
        self._view.SetItemNumber(*self._model.GetItems(volume, self._comparePage[code]), code=code)
        self._view.SetText(self._model.GetPage(volume, self._comparePage[code]), code=code)       
        self._view.FormatText(self._model.GetFormatter(volume, page), code=code)        
        self._LoadMarks(volume, page, code)        
        self._view.UpdateSlider(self._comparePage[code], self._model.GetFirstPageNumber(volume), self._model.GetTotalPages(volume), code)        
        self._model.Code = currentCode                

    def _HighlightKeywords(self, content, keywords):
        if content == u'' or keywords is None: return

        font = self._view.Body.GetFont()
        for term in keywords.replace('+',' ').replace('|',' ').split():
            n = -1
            while True:                    
                n = content.find(term, n+1)
                if n == -1: break
                self._view.Body.SetStyle(n, n+len(term), wx.TextAttr('purple', wx.NullColour, font))

    def OnLinkToReference(self, code, volume, item):
        self._DoCompare(code, volume, 1, item)

    def Close(self):
        self._bookmarkManager.Save()
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def Forward(self, code=None):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage+1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], self._comparePage[code] + 1)
        
    def Backward(self, code=None):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage-1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], self._comparePage[code] - 1)

    def HandleBookSelection(self, event):
        if isinstance(event, wx.TreeEvent):
            volume, page, section = self._view.BookList.GetItemPyData(event.GetItem())
            self.OpenBook(volume, page, section if section is not None else self._model.GetSection(volume, page))
        elif isinstance(event, wx.CommandEvent):
            self.OpenBook(event.GetSelection()+1, self._model.GetFirstPageNumber(event.GetSelection()+1))
            
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
            page = self._model.ConvertItemToPage(self._currentVolume, item, sub, self._view.CheckBox.IsChecked())
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

        sub = self._model.GetSubItem(self._currentVolume, self._currentPage, item)
        self._DoCompare(constants.CODES[index], self._currentVolume, sub, item)

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
        elif not flag and code is not None:
            self._focusList.remove(code)
        elif flag and code is None:
            self._focusList = []
    
    def ProcessKeyCommand(self, event, keyCode, code):
        ret = self._keyCommandHandler.Handle(event, keyCode)        
        if ret == constants.CMD_FIND:
            self.Find(code)
        elif ret == constants.CMD_FORWARD:
            self.Forward(code)
        elif ret == constants.CMD_BACKWARD:
            self.Backward(code)
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
        n = self._findTextHandler.Handle(text, content, flags)
        if n > -1:
            self._view.SetSelection(content, n, n+len(text), code)
            
    def ToggleBookList(self):
        self._view.ToggleBookList()
        
    def ShowFontDialog(self):
        curFont = utils.LoadFont(constants.READ_FONT)
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        if curFont != None:
            fontData.SetInitialFont(curFont)
        dialog = wx.FontDialog(self._view, fontData)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            if font.IsOk():
                utils.SaveFont(font, constants.READ_FONT)
                self._view.Font = font
        dialog.Destroy()

    def IncreaseFontSize(self):
        font = utils.LoadFont(constants.READ_FONT)
        font.SetPointSize(font.GetPointSize()+1)
        self._view.Font = font        
        utils.SaveFont(font, constants.READ_FONT)        
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        
    def DecreaseFontSize(self):
        font = utils.LoadFont(constants.READ_FONT)
        font.SetPointSize(font.GetPointSize()-1)
        self._view.Font = font
        utils.SaveFont(font, constants.READ_FONT)
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
        volume = self._currentVolume if code is None else self._compareVolume[code]
        page = self._currentPage if code is None else self._comparePage[code]
        return self._MarkKey(code, volume, page)
              
    def _CurrentMarkFilename(self, code):
        volume = self._currentVolume if code is None else self._compareVolume[code]
        page = self._currentPage if code is None else self._comparePage[code]        
        path = os.path.join(constants.MARKS_PATH, self._model.Code if code is None else code)        
        return os.path.join(path, '%02d-%04d.json'%(volume, page))        
                
    def SaveNoteText(self):
        self._view.NoteTextCtrl.SaveFile(self._view.NoteTextCtrl.GetFilename(), rt.RICHTEXT_TYPE_XML)
        self._view.NoteTextCtrl.SetModified(False)
        
    def SaveMarkedText(self, code):
        key = self._CurrentMarkKey(code)                
        filename = self._CurrentMarkFilename(code)
        
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
        return os.path.exists(self._CurrentMarkFilename(code))
        
    def HasMarkText(self, code):
        return any(map(lambda x:x[0], self._marks.get(self._CurrentMarkKey(code), [])))
        
    def ShowBookmarkPopup(self, x, y):
        self._view.ShowBookmarkPopup(x,y)
        
    def LoadBookmarks(self, menu):
        
        def OnBookmark(event):
            item = self._view.GetBookmarkMenuItem(event.GetId())
            text = utils.ThaiToArabic(item.GetText())
            tokens = text.split(' ')
            volume, page = int(tokens[1]), int(tokens[3])            
            self.OpenBook(volume, page, selectItem=True)
        
        self._bookmarkManager.MakeMenu(menu, OnBookmark)
        
    def SearchSelection(self):
        code = self._focusList[0] if len(self._focusList) > 0 else None
        keywords = self._view.GetStringSelection(code)
        
        if len(keywords.strip()) == 0: return

        self.Delegate.BringToFront()
        self.Delegate.Search(keywords, code)

    def _ToggleButtons(self, volume):
        getattr(self._view.BackwardButton, 'Disable' if self._currentPage <= self._model.GetFirstPageNumber(volume) else 'Enable')()
        getattr(self._view.ForwardButton, 'Disable' if self._currentPage >= self._model.GetTotalPages(volume) else 'Enable')()
        getattr(self._view.CompareComboBox, 'Disable' if self._currentPage == 0 else 'Enable')()

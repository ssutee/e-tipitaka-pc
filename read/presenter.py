# -*- coding:utf-8 -*-

import wx
import wx.richtext as rt
from wx.html import HtmlEasyPrinting
import constants, utils, dialogs, widgets
import os, json, codecs, re, sqlite3, sys

from pony.orm import Database, Required, Optional, db_session, select, desc
from read.model import Model
from utils import BookmarkManager

import cStringIO
import xhtml2pdf.pisa as pisa

import i18n
_ = i18n.language.ugettext

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
        self._filter = {3592: ord('.'), 3651: ord('0'), 3653: ord('1'), 47: ord('2'), 
                        95: ord('3'), 3616: ord('4'), 3606: ord('5'), 3640: ord('6'), 
                        3638: ord('7'), 3588: ord('8'), 3605: ord('9')}
        
    def Handle(self, event, code):
        code = self._filter.get(code, code) 

        if (event.CmdDown() or event.ControlDown()) and (code == ord('p') or code == 16):
            self._command = ''
            return constants.CMD_PRINT
        elif (event.CmdDown() or event.ControlDown()) and (code == ord('s') or code == 19):
            self._command = ''
            return constants.CMD_SAVE
        elif code == ord('+') or code == ord('='):
            self._command = ''
            return constants.CMD_ZOOM_IN
        elif code == ord('-'):
            self._command = ''
            return constants.CMD_ZOOM_OUT
        elif ((event.CmdDown() or event.ControlDown()) and code == ord('f')) or code == 6:
            self._command = ''
            return constants.CMD_FIND
        elif (event.CmdDown() or event.ControlDown()) and (event.AltDown() or event.ShiftDown()) and (code == 141 or code == 3):
            self._command = ''
            return constants.CMD_COPY_REFERENCE
        elif code == wx.WXK_LEFT:
            self._command = ''
            return constants.CMD_BACKWARD
        elif code == wx.WXK_RIGHT:
            self._command = ''
            return constants.CMD_FORWARD
        elif (code >= ord('0') and code <= ord('9')) or code == ord('.'):
            self._command += chr(code)
            return constants.CMD_IDLE
        elif code == ord('i') or code == ord('p') or code == ord('v') or code == 3618 or code == 3619 or code == 3629:
            self._result = self._command
            self._command = ''                
            if code == 3619 or code == ord('i'):
                return constants.CMD_JUMP_TO_ITEM
            elif code == 3618 or code == ord('p'):
                return constants.CMD_JUMP_TO_PAGE
            elif code == 3629 or code == ord('v'):
                return constants.CMD_JUMP_TO_VOLUME
            return constants.CMD_IDLE            

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
        
class Presenter(object):
    def __init__(self, model, view, interactor, code):
        self._stopOpen = False
        self._currentPage = 0
        self._currentVolume = 0
        self._code = code
        self._keywords = None
        self._paliDictWindow = None
        self._thaiDictWindow = None
        self._englishDictWindow = None
        
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
        self._view.Start()
        interactor.Install(self, view)     
        
        self._keyCommandHandler = KeyCommandHandler()
        self._findTextHandler = FindTextHandler()
        self._bookmarkManager = BookmarkManager(self._view, code)

        self._SetupPrinter()
        
        
    @property
    def View(self):
        return self._view

    @property
    def CurrentVolume(self):
        return self._currentVolume
        
    @property
    def CurrentPage(self):
        return self._currentPage
        
    @property
    def FocusVolume(self):
        return self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        
    @property
    def FocusPage(self):
        return self._currentPage if self._lastFocus is None else self._comparePage[self._lastFocus]        
        
    @property
    def LastFocus(self):
        return self._lastFocus
        
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

        body = self._view.Body
        font = body.GetFont()
        self._printer.SetStandardFonts(13)

        data = self._printer.GetPageSetupData()
        data.SetDefaultMinMargins(False)
        data.SetMarginTopLeft((10,20))
        data.SetMarginBottomRight((5,10))        

    def BringToFront(self):
        self._view.Activate()

    def _LoadNoteText(self, volume, page, code=None, index=1):
        textCtrl = self._view.NoteTextCtrl(code, index)

        textCtrl.SelectAll()
        textCtrl.DeleteSelection()        
        textCtrl.EndAllStyles()

        path = os.path.join(constants.NOTES_PATH, self._model.Code)
        if not os.path.exists(path):
            os.makedirs(path)  
        filename = os.path.join(path, '%02d-%04d.xml'%(volume, page))
        textCtrl.SetFilename(filename)
        if os.path.exists(filename):
            textCtrl.LoadFile(filename, rt.RICHTEXT_TYPE_XML)        
        textCtrl.SetModified(False)

    def _MarkKey(self, code, volume, page):
        code = self._model.Code if code is None else code
        return '%s-%02d-%04d' % (code, volume, page)

    def _LoadMarks(self, volume, page, code=None, index=1):
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
            self._view.MarkText(code, index, (s,t)) if marked else self._view.UnmarkText(code, index, (s,t))

    def OpenBook(self, volume, page, section=None, selectItem=False, showBookList=None, focus=True):
        self._findTextHandler.Reset()

        page = self._model.GetFirstPageNumber(volume) if page < self._model.GetFirstPageNumber(volume) else page

        self._currentVolume = volume
        self._currentPage = page

        if self._model.GetTotalPages(volume) == 0: 
            self._view.SetText(u'ฐานข้อมูลยังจัดทำไม่เสร็จ', focus=focus)
            self._view.SetText(u'ฐานข้อมูลยังจัดทำไม่เสร็จ', focus=focus)
            return

        if page > self._model.GetTotalPages(volume) or page < self._model.GetFirstPageNumber(volume): return

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
        self._view.SetText(content, focus=focus)        
        self._view.SetText(content, focus=focus)
        self.SetStatusText(u'', 0)        
        self.SetStatusText(u'คำค้นหาคือ "%s"'%(self._keywords) if self._keywords is not None and len(self._keywords) > 0 else u'', 1)

        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))

        self._HighlightKeywords(content, self._keywords, volume, page)        
        self._HighlightItems(content)
        self._LoadMarks(self._currentVolume, self._currentPage)
        
        if hasattr(self._delegate, 'OnReadWindowOpenPage'):
            self._delegate.OnReadWindowOpenPage(self._currentVolume, self._currentPage, self._code)

        self._stopOpen = True
        if selectItem: self._view.SetBookListSelection(self._currentVolume)        
        self._stopOpen = False

        if showBookList != None and showBookList == True:
            self._view.ShowBookList()
        elif showBookList != None and showBookList == False:
            self._view.HideBookList()

    def OpenAnotherBook(self, code, index, volume, page, keywords=None, focus=True):
        self._findTextHandler.Reset()        
        currentCode = self._model.Code
        self._model.Code = code
        
        if page > self._model.GetTotalPages(volume) or page < self._model.GetFirstPageNumber(volume): return

        key = utils.MakeKey(code, index)
        self._compareVolume[key] = volume        
        self._comparePage[key] = page        
        
        self._LoadNoteText(volume, page, code, index)
                
        self._ToggleNavigationButtons(self._compareVolume[key], code, index)
                
        self._view.SetTitles(*self._model.GetTitles(volume, None), code=code, index=index)        
        self._view.SetPageNumber(page if page > 0 else None, code=code, index=index)
        self._view.SetItemNumber(*self._model.GetItems(volume, page), code=code, index=index)
        self._view.UpdateSlider(page, self._model.GetFirstPageNumber(volume), self._model.GetTotalPages(volume), code, index)
        
        content = self._model.GetPage(volume, page)
        self._view.SetText(content, code=code, index=index, focus=focus)
        self._view.FormatText(self._model.GetFormatter(volume, page), code=code, index=index)        
        if keywords is not None:
            self._HighlightKeywords(content, keywords, volume, page, code, index)
        self._HighlightItems(content, code, index)
        self._LoadMarks(volume, page, code, index)

        self._model.Code = currentCode                

    def _HighlightItems(self, content, code=None, index=1):
        n = -1
        for item in re.findall(ur'({[๐๑๒๓๔๕๖๗๘๙0-9\.:;]+})', content):
            n = content.find(item, n+1)
            
            body = self._view.Body if code == None else self._view.FocusBody(code, index)

            if wx.__version__[:3]<='2.8':
                body.Freeze()

            font = body.GetFont()
            colorCode, diffSize = constants.FOOTER_STYLE
            body.SetStyle(n, n+len(item), wx.TextAttr(colorCode, wx.NullColour, font))

            if wx.__version__[:3]<='2.8':
                body.Thaw()


    def _HighlightKeywords(self, content, keywords, volume, page, code=None, index=1):
        if content == u'' or keywords is None: return

        body = self._view.Body if code == None else self._view.FocusBody(code, index)

        font = body.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        fontSize = font.GetPointSize()
        for term in keywords.replace('+',' ').replace('|',' ').split():
            n = -1
            while True:                    
                n = content.find(self._model.ConvertSpecialCharacters(term), n+1)
                if n == -1: break                

                if wx.__version__[:3]<='2.8':
                    body.Freeze()
                
                checkBuddhawaj = False
                for format in self._model.GetFormatter(volume, page).split():
                    tag, s, e = format.split('|')
                    s, e = int(s), int(e)
                    if tag == 'eh1' and n >= s and n+len(term) <= e:
                        font.SetPointSize(fontSize * 1.2)
                        checkBuddhawaj = True
                    elif tag == 'eh2' and n >= s and n+len(term) <= e:
                        font.SetPointSize(fontSize * 0.85)
                    elif tag == 'eh3' and n >= s and n+len(term) <= e:
                        font.SetPointSize(fontSize * 0.75)
                    elif tag == 'fn' and n >= s and n+len(term) <= e:
                        font.SetPointSize(fontSize * 0.8)

                if (self._delegate.SearchingBuddhawaj() and checkBuddhawaj) or not self._delegate.SearchingBuddhawaj():
                    body.SetStyle(n, n+len(term), wx.TextAttr('purple', wx.NullColour, font))

                if wx.__version__[:3]<='2.8':
                    body.Thaw()

    def OnLinkToReference(self, code, volume, item):
        self._view.HideBookList()
        index = self._view.AddReadPanel(code)
        
        currentCode = self._model.Code
        
        self._model.Code = code

        volume, page = self._model.ConvertFromPivot(volume, item, 1)
        
        self._model.Code = currentCode 

        if volume == 0:
            return

        self.OpenAnotherBook(code, index, volume, page)                

    def SaveBookmark(self):        
        self._bookmarkManager.Save()

    def Close(self):
        self._stopOpen = True
        self.SaveBookmark()        
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code, self)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def _DoForward(self, code=None, index=1):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage+1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:            
            key = utils.MakeKey(code, index)
            self.OpenAnotherBook(code, index, self._compareVolume[key], self._comparePage[key] + 1)

    def Forward(self, code=None):        
        code, index = utils.SplitKey(self._lastFocus)
        self._DoForward(code, index)
        
    def _DoBackward(self, code=None, index=1):
        if code is None:
            self.OpenBook(self._currentVolume, self._currentPage-1, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            key = utils.MakeKey(code, index)
            self.OpenAnotherBook(code, index, self._compareVolume[key], self._comparePage[key] - 1)
                
    def Backward(self, code=None):
        code, index = utils.SplitKey(self._lastFocus)
        self._DoBackward(code, index)

    def HandleBookSelection(self, event):
        if self._stopOpen: return
        
        if isinstance(event, wx.TreeEvent):
            volume, page, section = self._view.BookList.GetItemPyData(event.GetItem())
            self.OpenBook(volume, page, section if section is not None else self._model.GetSection(volume, page))
        elif isinstance(event, wx.CommandEvent):
            self.OpenBook(event.GetSelection()+1, self._model.GetFirstPageNumber(event.GetSelection()+1))

    def HandleTextSelection(self, text, code, index):
        text = text.strip().split('\n')[0]        
        self.SetStatusText(u'คำที่เลือกคือ "%s"' % text if len(text) > 0 else u'', 0)
        if self._paliDictWindow is not None:            
            self._paliDictWindow.SetInput(text)
        if self._thaiDictWindow is not None:
            self._thaiDictWindow.SetInput(text)
        if self._englishDictWindow is not None:
            self._englishDictWindow.SetInput(text)
            
    def JumpToPage(self, page, code=None, index=1):
        if code is None:
            page = page if page > 0 and page <= self._model.GetTotalPages(self._currentVolume) else self._model.GetFirstPageNumber(self._currentVolume)
            self.OpenBook(self._currentVolume, page, self._model.GetSection(self._currentVolume, page), focus=False)
        else:            
            self.OpenAnotherBook(code, index, self._compareVolume[utils.MakeKey(code, index)], page, focus=False)
        
    def JumpToItem(self, item, code=None, index=1):
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
            page = self._model.ConvertItemToPage(self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code, index)], item, sub, self._view.CheckBox.IsChecked())
            self._model.Code = currentCode
        except ValueError, e:
            pass
            
        self.JumpToPage(page, code, index)

    def _CloseDictWindow(self):
        if self._paliDictWindow is not None:
            self._paliDictWindow.Close()
            self._paliDictWindow = None

        if self._thaiDictWindow is not None:
            self._thaiDictWindow.Close()
            self._thaiDictWindow = None

        if self._englishDictWindow is not None:
            self._englishDictWindow.Close()
            self._englishDictWindow = None


    def CompareTo(self, index):
        self._CloseDictWindow()
        
        item = None    
        items = self._model.GetItems(self._currentVolume, self._currentPage)
        if len(items) > 1 and self._model.CanSelectComparingItem():
            dialog = wx.SingleChoiceDialog(self._view, u'เลือกข้อที่ต้องการเทียบเคียง', 
                self._model.GetTitle(self._currentVolume), map(lambda x: u'ข้อที่ ' + utils.ArabicToThai(x), items))
            if dialog.ShowModal() == wx.ID_OK:
                item = items[dialog.GetSelection()]
            dialog.Destroy()
        elif len(items) > 0:
            item = items[0]
        
        self._DoCompare(constants.CODES[constants.COMPARE_ORDER[index]], item)

    def _DoCompare(self, code, item):        
        if item is None: return
        
        self._view.HideBookList()
        index = self._view.AddReadPanel(code)
        
        volume, item, sub = self._model.ConvertToPivot(self._currentVolume, self._currentPage, item)
        
        if volume == 0:
            return

        currentCode = self._model.Code
        self._model.Code = code

        volume, page = self._model.ConvertFromPivot(volume, item, sub)
        
        self._model.Code = currentCode 

        if volume == 0:
            return

        self.OpenAnotherBook(code, index, volume, page)

    def SetFocus(self, flag, code, index):
        if flag and code is not None:            
            self._focusList.append(utils.MakeKey(code, index))
            self._lastFocus = utils.MakeKey(code, index)
        elif not flag and code is not None and utils.MakeKey(code, index) in self._focusList:
            self._focusList.remove(utils.MakeKey(code, index))
        elif flag and code is None:
            self._focusList = []
            self._lastFocus = None        
                        
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        if self._lastFocus is None:
            self._ToggleNavigationButtons(volume, self._lastFocus, 1)
        else:
            c,idx = utils.SplitKey(self._lastFocus)
            self._ToggleNavigationButtons(volume, c, idx)
    
    def ProcessKeyCommand(self, event, keyCode, code, index):
        ret = self._keyCommandHandler.Handle(event, keyCode)        
        if ret == constants.CMD_FIND:
            self.Find(code, index)
        elif ret == constants.CMD_FORWARD:
            self._DoForward(code, index)
        elif ret == constants.CMD_BACKWARD:
            self._DoBackward(code, index)
        elif ret == constants.CMD_JUMP_TO_PAGE:
            self.JumpToPage(int(self._keyCommandHandler.Result), code, index)
        elif ret == constants.CMD_JUMP_TO_ITEM:
            self.JumpToItem(self._keyCommandHandler.Result, code, index)
        elif ret == constants.CMD_JUMP_TO_VOLUME:
            volume = int(self._keyCommandHandler.Result)
            self.OpenAnotherBook(code, index, volume, 1) if code is not None else self.OpenBook(volume, 1, selectItem=True)
        elif ret == constants.CMD_ZOOM_IN:
            self.IncreaseFontSize()
        elif ret == constants.CMD_ZOOM_OUT:
            self.DecreaseFontSize()
        elif ret == constants.CMD_COPY_REFERENCE:
            self.CopyReference()
        elif ret == constants.CMD_SAVE:
            self.ShowSaveDialog()
        elif ret == constants.CMD_PRINT:
            self.ShowPrintDialog()
            
    def CopyReference(self, window=None, code=None):
        clipdata = wx.TextDataObject()        
        code, index = utils.SplitKey(self._lastFocus)
        ref = self.GetReference(code, index)        

        window = self._view.FocusBody(code, index) if window is None else window        
        if isinstance(window, wx.html.HtmlWindow):
            clipdata.SetText(window.SelectionToText() + '\n\n\n' + ref)
        elif isinstance(window, wx.TextCtrl):
            clipdata.SetText(window.GetStringSelection() + '\n\n\n' + ref)
            
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()                
    
    def Find(self, code, index):
        self._view.ShowFindDialog(code, index, self._findTextHandler.Text, self._findTextHandler.Direction)
        
    def DoFind(self, code, index, text, content, flags):
        n, found = self._findTextHandler.Handle(text, content, flags)
        if n > -1:
            self._view.SetSelection(content, n, n+len(text), code, index)
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
        
    def ToggleNotePanel(self, code, index):
        self._view.ToggleNotePanel(code, index)
        
    def ShowFontDialog(self, target=constants.READ_FONT):
        code = None
        if target == constants.READ_FONT:
            code, index = utils.SplitKey(self._lastFocus)

        curFont = utils.LoadFont(target, code if code else self._model.Code)
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        if curFont != None:
            fontData.SetInitialFont(curFont)
        dialog = dialogs.SimpleFontDialog(self._view, fontData) if 'wxMac' in wx.PlatformInfo else wx.FontDialog(self._view, fontData)
        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            font = data.GetChosenFont()
            if font.IsOk():
                utils.SaveFont(font, target, code if code else self._model.Code) 
                if target == constants.READ_FONT:               
                    self._view.SetFont(font, code, index)
                elif target == constants.BOOK_FONT:
                    self._view.BookList.SetFont(font)
                    
        dialog.Destroy()

    def IncreaseFontSize(self):
        code, index = utils.SplitKey(self._lastFocus)
        font = utils.LoadFont(constants.READ_FONT, code if code else self._model.Code)
        font.SetPointSize(font.GetPointSize()+1)
        utils.SaveFont(font, constants.READ_FONT, code if code else self._model.Code)        
        self._view.SetFont(font, code, index)    
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        content = self._model.GetPage(self._currentVolume, self._currentPage)
        self._HighlightKeywords(content, self._keywords, self._currentVolume, self._currentPage)
        self._HighlightItems(content)
        
    def DecreaseFontSize(self):
        code, index = utils.SplitKey(self._lastFocus)
        font = utils.LoadFont(constants.READ_FONT, code if code else self._model.Code)
        font.SetPointSize(font.GetPointSize()-1)
        utils.SaveFont(font, constants.READ_FONT, code if code else self._model.Code)
        self._view.SetFont(font, code, index)
        self._view.FormatText(self._model.GetFormatter(self._currentVolume, self._currentPage))
        content = self._model.GetPage(self._currentVolume, self._currentPage)
        self._HighlightKeywords(content, self._keywords, self._currentVolume, self._currentPage)
        self._HighlightItems(content)

    def MarkText(self, code, index, mark=True):
        s,t = self._view.MarkText(code, index) if mark else self._view.UnmarkText(code, index)
        volume = self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code,index)]
        page = self._currentPage if code is None else self._comparePage[utils.MakeKey(code,index)]
        key = self._MarkKey(code, volume, page)
        if key not in self._marks:
            self._marks[key] = [(mark, s, t)]
        else:
            self._marks[key] += [(mark, s, t)]

    def UnmarkText(self, code, index):
        self.MarkText(code, index, False)        
            
    def GetReference(self, code, index):
        
        model = Model(code if code is not None else self._model.Code)

        volume = self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code,index)]
        page = self._currentPage if code is None else self._comparePage[utils.MakeKey(code,index)]
        items = model.GetItems(volume, page)
        titles = model.GetTitles(volume, None)        

        ref = titles[0] + '  '

        if len(titles[1]) > 0:
            ref += titles[1] + '  '
            
        ref += _('Page') + ' ' + utils.ArabicToThai(unicode(page))

        if len(items) != 0 and items[0] is not None:
            ref += '  ' + _('Item') + ' ' + utils.ArabicToThai(unicode(items[0]))
            if len(items) > 1:
                ref += ' - ' + utils.ArabicToThai(unicode(items[-1]))

        return ref                        
    
    def IndentLessNoteText(self, textCtrl):
        attr = rt.RichTextAttr()
        attr.SetFlags(wx.TEXT_ATTR_LEFT_INDENT)
        ip = textCtrl.GetInsertionPoint()
        if textCtrl.GetStyle(ip, attr):
            r = rt.RichTextRange(ip, ip)
            if textCtrl.HasSelection():
                r = textCtrl.GetSelectionRange()

        if attr.GetLeftIndent() >= 100:
            attr.SetLeftIndent(attr.GetLeftIndent() - 100)
            attr.SetFlags(wx.TEXT_ATTR_LEFT_INDENT)
            textCtrl.SetStyle(r, attr)
    
    def IndentMoreNoteText(self, textCtrl):
        attr = rt.RichTextAttr()
        attr.SetFlags(wx.TEXT_ATTR_LEFT_INDENT)
        ip = textCtrl.GetInsertionPoint()
        if textCtrl.GetStyle(ip, attr):
            r = rt.RichTextRange(ip, ip)
            if textCtrl.HasSelection():
                r = textCtrl.GetSelectionRange()

            attr.SetLeftIndent(attr.GetLeftIndent() + 100)
            attr.SetFlags(wx.TEXT_ATTR_LEFT_INDENT)
            textCtrl.SetStyle(r, attr)
            
    def ApplyFontToNoteText(self, textCtrl):
        if not textCtrl.HasSelection():
            return

        r = textCtrl.GetSelectionRange()
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        attr = rt.RichTextAttr()
        attr.SetFlags(wx.TEXT_ATTR_FONT)
        if textCtrl.GetStyle(textCtrl.GetInsertionPoint(), attr):
            fontData.SetInitialFont(attr.GetFont())

        dlg = dialogs.SimpleFontDialog(self._view, fontData) if 'wxMac' in wx.PlatformInfo else wx.FontDialog(self._view, fontData)
        if dlg.ShowModal() == wx.ID_OK:
            fontData = dlg.GetFontData()
            font = fontData.GetChosenFont()
            if font:
                attr.SetFlags(wx.TEXT_ATTR_FONT)
                attr.SetFont(font)
                textCtrl.SetStyle(r, attr)
        dlg.Destroy()

    def ApplyFontColorToNoteText(self, textCtrl):
        colourData = wx.ColourData()
        attr = rt.RichTextAttr()
        attr.SetFlags(wx.TEXT_ATTR_TEXT_COLOUR)
        if textCtrl.GetStyle(textCtrl.GetInsertionPoint(), attr):
            colourData.SetColour(attr.GetTextColour())

        dlg = wx.ColourDialog(self._view, colourData)
        if dlg.ShowModal() == wx.ID_OK:
            colourData = dlg.GetColourData()
            colour = colourData.GetColour()
            if colour:
                if not textCtrl.HasSelection():
                    textCtrl.BeginTextColour(colour)
                else:
                    r = textCtrl.GetSelectionRange()
                    attr.SetFlags(wx.TEXT_ATTR_TEXT_COLOUR)
                    attr.SetTextColour(colour)
                    textCtrl.SetStyle(r, attr)
        dlg.Destroy()
        
    def _CurrentMarkKey(self, code, index):
        if code is not None and (utils.MakeKey(code, index) not in self._compareVolume or utils.MakeKey(code, index) not in self._comparePage): 
            return None
        volume = self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code, index)]
        page = self._currentPage if code is None else self._comparePage[utils.MakeKey(code, index)]
        return self._MarkKey(code, volume, page)
              
    def _CurrentMarkFilename(self, code, index):
        if code is not None and (utils.MakeKey(code, index) not in self._compareVolume or utils.MakeKey(code, index) not in self._comparePage): 
            return None
        volume = self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code, index)]
        page = self._currentPage if code is None else self._comparePage[utils.MakeKey(code, index)]        
        path = os.path.join(constants.MARKS_PATH, self._model.Code if code is None else code)        
        return os.path.join(path, '%02d-%04d.json'%(volume, page))        
    
    @db_session            
    def SaveNoteText(self, code, index, textCtrl):        
        textCtrl.SaveFile(textCtrl.GetFilename(), rt.RICHTEXT_TYPE_XML)
        textCtrl.SetModified(False)

        volume = self._currentVolume if code is None else self._compareVolume[utils.MakeKey(code,index)]
        page = self._currentPage if code is None else self._comparePage[utils.MakeKey(code,index)]        
        
        conn = sqlite3.connect(constants.NOTE_DB)
        cursor = conn.cursor()

        filename = textCtrl.GetFilename()
        text = textCtrl.GetValue()

        real_code = code if code is not None else self._model.Code

        cursor.execute('SELECT * FROM Note WHERE volume=? AND page=? AND code=?', (volume, page, real_code))
        if cursor.fetchone() and text != u'':
            cursor.execute('UPDATE Note SET text=? WHERE volume=? AND page=? AND code=?', (text, volume, page, real_code))
        elif text != u'':
            cursor.execute('INSERT INTO Note (volume,page,code,filename,text) VALUES (?,?,?,?,?)', 
                           (volume, page, real_code, filename, text))
        else:
            cursor.execute('DELETE FROM Note WHERE volume=? AND page=? AND code=?', (volume, page, real_code))

        conn.commit()
        conn.close()
                        
    def SaveMarkedText(self, code, index):
        key = self._CurrentMarkKey(code, index)                
        filename = self._CurrentMarkFilename(code, index)

        if filename is None or key is None: return
        
        if key not in self._marks or len(self._marks[key]) == 0: 
            os.remove(filename) if os.path.exists(filename) else None
        else:
            with open(filename, 'w') as f: json.dump(self._marks[key], f)
        
    def ClearMarkedText(self, code, index):
        dlg = wx.MessageDialog(self._view.ReadPanel(code, index), u'คุณต้องการลบการระบายสีข้อความทั้งหมดหรือไม่?', u'ยืนยันการลบ', 
            wx.YES_NO|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self._marks[self._CurrentMarkKey(code, index)] = []
            self._view.ClearMarks(code, index)
            self.SaveMarkedText(code, index)
        dlg.Destroy()
        
    def HasSavedMark(self, code, index):        
        return os.path.exists(self._CurrentMarkFilename(code, index)) if self._CurrentMarkFilename(code, index) is not None else False
        
    def HasMarkText(self, code, index):
        return any(map(lambda x:x[0], self._marks.get(self._CurrentMarkKey(code, index), [])))
        
    def ShowBookmarkPopup(self, x, y):
        code, index = utils.SplitKey(self._lastFocus)
        self._view.ShowBookmarkPopup(x, y, code, index)
        
    def ShowPrintDialog(self):       
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        page = self._currentPage if self._lastFocus is None else self._comparePage[self._lastFocus]
        
        currentCode = self._model.Code
        self._model.Code = currentCode if self._lastFocus is None else self._lastFocus
        
        title1, title2 = self._model.GetTitles(volume)
        total = self._model.GetTotalPages(volume)

        data = {'from':page-1 if page > 0 else 0, 'to':page-1 if page > 0 else 0, 'sep':False}
        dlg = dialogs.PageRangeDialog(self._view, u'โปรดเลือกหน้าที่ต้องการพิมพ์', title1, title2, total, data)
        
        if dlg.ShowModal() == wx.ID_OK:
            font = utils.LoadFont(constants.READ_FONT, self._model.Code)

            app_path = os.path.dirname(os.path.realpath(sys.argv[0]))
            font_path = os.path.join(app_path, 'fonts','TF Chiangsaen.ttf')
            
            style = '<style>\n'
            style += '@font-face { font-family: "TF Chiangsaen"; src: url(\'%s\') } \n' % font_path
            style += 'body { font-family: "TF Chiangsaen"; font-size: 26px; line-height: 1; } \n'
            style += '</style>'

            text = u'<body>'
            
            ptext = u'หน้าที่ %s ถึง %s' % (utils.ArabicToThai(str(data['from']+1).decode('utf8','ignore')), 
                utils.ArabicToThai(str(data['to']+1).decode('utf8','ignore')))
            if data['from'] == data['to']:
                ptext = u'หน้าที่ %s' % (utils.ArabicToThai(str(data['from']+1).decode('utf8','ignore')))                
            
            text += u"<div align=center><b>%s</b><br><b>%s</b><br>%s</div><hr>" % (title1, title2, ptext)
            
            for p in range(data['from'], data['to']+1) if data['from'] <= data['to'] else range(data['from'], data['to']-1, -1):
                content = self._model.GetPage(volume, p+1).replace(u'\t', u'&nbsp;'*7).replace(u'\x0a', u'<br>')
                content = content.replace(u'\x0b', u'<br>').replace(u'\x0c', u'<br>').replace(u'\x0d', u'<br>')

                if data['sep']:
                    text += u'<div align=right>หน้าที่ %s</div>'%(utils.ArabicToThai(str(p+1).decode('utf8','ignore')))
                    text += u'%s<br><br>'%(content)
                else:
                    text += u'%s<br>'%(content)
                    
            text = text.rstrip('<br>') + u'</body>'

            dest = os.path.join(constants.DATA_PATH, 'printing.pdf')
            
            html = '<html>' + style + text + '</html>'

            pdf = pisa.CreatePDF(cStringIO.StringIO(html.encode('utf-8')), file(dest, "wb"), encoding='utf-8')
            if pdf.err:
                print pdf.err
            else:
                pisa.startViewer(dest)

        dlg.Destroy()
    
        self._model.Code = currentCode

    def _ShowConfirmSaveDialog(self, code, volume, start, end, text):
        dlg = wx.FileDialog(self._view, u'โปรดเลือกไฟล์', self._saveDirectory, 
            '%s_volumn-%02d_page-%04d-%04d' % (code, volume, start+1, end+1), 
            u'Plain Text (*.txt)|*.txt', wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            with codecs.open(os.path.join(dlg.GetDirectory(), dlg.GetFilename()), 'w', 'utf-8') as f:
                f.write(text)
            self._saveDirectory = dlg.GetDirectory()                
        dlg.Destroy()
        
    def _SavePagesToText(self, title1, title2, volume, start, end, sep):
        text = u'%s\n%s\n\n' % (title1, title2)
        for p in range(start, end+1) if start <= end else range(start, end-1, -1):
            content = self._model.GetPage(volume, p+1)
            text += u' '*60 + u'หน้าที่ %s\n\n'%(utils.ArabicToThai(str(p+1).decode('utf8','ignore'))) if sep else ''
            text += u'%s\n\n\n' % (content)
        self._ShowConfirmSaveDialog(self._model.Code, volume, start, end, text)

    def _SavePagesToPDF(self, volume, start, end):
        import urllib2, webbrowser
        start, end = (end, start) if start > end else (start, end)
        url = constants.PALI_PDF_URL_PATTERN % (volume, start+1, end+1)
        response = urllib2.urlopen(url).read()
        obj = json.loads(response)
        if obj.get('success', False):
            webbrowser.open_new(obj.get('url'))
        else:
            dlg = wx.MessageDialog(self._view, 
                                   u'เนื่องจากข้อมูลยังไม่สมบูรณ์ กรุณาทดลองใหม่ภายหลัง', 
                                   u'ไม่พบไฟล์ PDF ต้นฉบับ', style=wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        
    def ShowSaveDialog(self):
        volume = self._currentVolume if self._lastFocus is None else self._compareVolume[self._lastFocus]
        page = self._currentPage if self._lastFocus is None else self._comparePage[self._lastFocus]
        
        currentCode = self._model.Code
        self._model.Code = currentCode if self._lastFocus is None else self._lastFocus
        
        title1, title2 = self._model.GetTitles(volume)
        total = self._model.GetTotalPages(volume)

        data = {'from':page-1 if page > 0 else 0, 'to':page-1 if page > 0 else 0}
        dlg = dialogs.PageRangeDialog(self._view, u'โปรดเลือกหน้าที่ต้องการบันทึก', title1, title2, total, data, self._model.HasPdf)        
        if dlg.ShowModal() == wx.ID_OK:
            if data.get('pdf', False):
                self._SavePagesToPDF(volume, data['from'], data['to'])
            else:
                self._SavePagesToText(title1, title2, volume, data['from'], data['to'], data['sep'])
        dlg.Destroy()
    
        self._model.Code = currentCode        
        
    def LoadBookmarks(self, menu, code, index):
        
        def OnBookmark(event):
            item = self._view.GetBookmarkMenuItem(event.GetId())
            text = utils.ThaiToArabic(item.GetText())
            tokens = text.split(' ')
            volume, page = int(tokens[1]), int(tokens[3])    
            if code is None:        
                self.OpenBook(volume, page, selectItem=True)
            else:
                self.OpenAnotherBook(code, index, volume, page)
                
        self._bookmarkManager = BookmarkManager(self._view, code if code is not None else self._model.Code)
        self._bookmarkManager.MakeMenu(menu, OnBookmark)
        
    def SearchSelection(self, selection=None):
        code, index = utils.SplitKey(self._lastFocus)
        keywords = self._view.GetStringSelection(code, index) if selection is None else selection
        
        if len(keywords.strip()) == 0: return

        self.Delegate.BringToFront()
        self.Delegate.Search(utils.ConvertToThaiSearch(keywords), code if code is not None else self._model.Code)

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
        text = self._view.GetStringSelection(self._lastFocus)
        self._paliDictWindow.SetInput(text.strip().split('\n')[0].strip())

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
        text = self._view.GetStringSelection(self._lastFocus)
        self._thaiDictWindow.SetInput(text.strip().split('\n')[0].strip())

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
        text = self._view.GetStringSelection(self._lastFocus)
        self._englishDictWindow.SetInput(text.strip().split('\n')[0].strip())
        
    def ShowContextMenu(self, window, position, code, index):
        self._view.ShowContextMenu(window, position, code, index)
        
    def ShowMarkManager(self):
        self._CloseDictWindow()

        code, index = utils.SplitKey(self._lastFocus) 
        dlg = dialogs.MarkManagerDialog(self._view.ReadPanel(code, index), 
                                        code if code is not None else self._model.Code, self._model)
        dlg.Delegate = self._model
        if dlg.ShowModal() == wx.ID_OK:
            volume, page, c = dlg.Result
            if self._lastFocus is not None:
                self.OpenAnotherBook(code, index, volume, page)  
            else:
                self.OpenBook(volume, page, selectItem=True)
        dlg.Destroy()

    def ShowNotesManager(self):
        self._CloseDictWindow()
        
        code, index = utils.SplitKey(self._lastFocus)                
        dlg = dialogs.NoteManagerDialog(self._view.ReadPanel(code, index), code if code is not None else self._model.Code)
        if dlg.ShowModal() == wx.ID_OK:
            volume, page, c = dlg.Result
            if self._lastFocus is not None:
                self.OpenAnotherBook(code, index, volume, page)  
            else:
                self.OpenBook(volume, page, selectItem=True)
        dlg.Destroy()

    def _ToggleCompareComboBox(self, volume):
        getattr(self._view.CompareComboBox, 'Disable' if self._currentPage == 0 else 'Enable')()
    
    def _ToggleNavigationButtons(self, volume, code=None, index=1):
        if code == None:
            getattr(self._view.BackwardButton, 'Disable' if self._currentPage <= self._model.GetFirstPageNumber(volume) else 'Enable')()
            getattr(self._view.ForwardButton, 'Disable' if self._currentPage >= self._model.GetTotalPages(volume) else 'Enable')()
        else:
            currentCode = self._model.Code
            self._model.Code = code
            key = utils.MakeKey(code,index)
            getattr(self._view.BackwardButton, 'Disable' if self._comparePage[key] <= self._model.GetFirstPageNumber(volume) else 'Enable')()
            getattr(self._view.ForwardButton, 'Disable' if self._comparePage[key] >= self._model.GetTotalPages(volume) else 'Enable')()            
            self._model.Code = currentCode
            
    def IsSmallScreen(self):
        currentScreen = wx.GetDisplaySize()
        return currentScreen[1] < 800

    def SelectTheme(self, theme):
        utils.SaveTheme(theme, constants.READ)
        for key in [None]+self._compareVolume.keys():
            code, index = utils.SplitKey(key)
            self._view.FocusBody(code, index).SetBackgroundColour(utils.LoadThemeBackgroundColour(constants.READ))
            self._view.FocusBody(code, index).SetForegroundColour(utils.LoadThemeForegroundColour(constants.READ))
            if code is None:            
                self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))        
            else:
                self.OpenAnotherBook(code, index, self._compareVolume[key], self._comparePage[key])            

    def SetStatusText(self, text, field):
        self._view.SetStatusText(text, field)
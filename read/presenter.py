#-*- coding:utf-8 -*-

import wx
import constants, utils

class KeyCommandHandler(object):
    def __init__(self):
        self._command = ''
        self._filter = {3653:49, 47:50, 45:51, 3616:52, 3606:53, 3640:54, 3638:55, 3588:56, 3605:57, 3592:48, 3651:46}
        
    def handle(self, code):
        code = self._filter.get(code, code)
        
        if code == wx.WXK_LEFT:
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

class Presenter(object):
    def __init__(self, model, view, interactor, code):
        self._code = code
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
        
        self._keyCommandHandler = KeyCommandHandler()

    @property
    def Delegate(self):
        return self._delegate
        
    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    def BringToFront(self):
        self._view.Raise()
        self._view.Iconize(False)

    def OpenBook(self, volume, page, section=None):
        self._currentVolume = volume
        self._currentPage = self._model.GetFirstPageNumber(self._currentVolume) if page < self._model.GetFirstPageNumber(self._currentVolume) else page
                
        self._ToggleButtons(self._currentVolume)

        self._view.SetTitles(*self._model.GetTitles(self._currentVolume, section))
        self._view.SetPageNumber(self._currentPage if self._currentPage > 0 else None)
        self._view.SetItemNumber(*self._model.GetItems(self._currentVolume, self._currentPage))

        self._view.SetText(self._model.GetPage(self._currentVolume, self._currentPage))
        self._view.UpdateSlider(self._currentPage, self._model.GetFirstPageNumber(self._currentVolume), 
            self._model.GetTotalPages(self._currentVolume))
            
    def OpenAnotherBook(self, code, volume, page):
        currentCode = self._model.Code
        self._model.Code = code
        if page <= self._model.GetTotalPages(volume) and page >= self._model.GetFirstPageNumber(volume):
            self._compareVolume[code] = volume        
            self._comparePage[code] = page
            self._view.SetTitles(*self._model.GetTitles(volume, None), code=code)        
            self._view.SetPageNumber(self._comparePage[code] if self._comparePage[code] > 0 else None, code=code)
            self._view.SetItemNumber(*self._model.GetItems(volume, self._comparePage[code]), code=code)
            self._view.SetText(self._model.GetPage(volume, self._comparePage[code]), code=code)       
            self._view.UpdateSlider(self._comparePage[code], self._model.GetFirstPageNumber(volume), self._model.GetTotalPages(volume), code)        
        self._model.Code = currentCode                

    def Close(self):
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def Forward(self, code=None):
        if code is None:
            self._currentPage += 1
            self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))
        else:
            self.OpenAnotherBook(code, self._compareVolume[code], self._comparePage[code] + 1)
        
    def Backward(self, code=None):
        if code is None:
            self._currentPage -= 1
            self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))
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

        if item is not None:    
            self._view.AddReadPanel(constants.CODES[index])
            currentCode = self._model.Code
            self._model.Code = constants.CODES[index]                        
            volume = self._model.ConvertVolume(self._currentVolume, item, sub)
            page = self._model.ConvertItemToPage(volume, item, sub, constants.CODES[index] == constants.THAI_MAHACHULA_CODE)
            self._model.Code = currentCode                    
            self.OpenAnotherBook(constants.CODES[index], volume, page)

    def SetFocus(self, flag, code):
        if flag and code is not None:
            self._focusList.append(code)
        elif not flag and code is not None:
            self._focusList.remove(code)
        elif flag and code is None:
            self._focusList = []
    
    def ProcessKeyCommand(self, keyCode, code):
        ret = self._keyCommandHandler.handle(keyCode)        
        if ret == constants.CMD_FORWARD:
            self.Forward(code)
        elif ret == constants.CMD_BACKWARD:
            self.Backward(code)
        elif ret == constants.CMD_JUMP_TO_PAGE:
            self.JumpToPage(int(self._keyCommandHandler.Result), code)
        elif ret == constants.CMD_JUMP_TO_ITEM:
            self.JumpToItem(self._keyCommandHandler.Result, code)
        elif ret == constants.CMD_JUMP_TO_VOLUME:
            volume = int(self._keyCommandHandler.Result)
            self.OpenAnotherBook(code, volume, 1) if code is not None else self.OpenBook(volume, 1)
        elif ret == constants.CMD_ZOOM_IN:
            pass
        elif ret == constants.CMD_ZOOM_OUT:
            pass

    def _ToggleButtons(self, volume):
        getattr(self._view.BackwardButton, 'Disable' if self._currentPage <= self._model.GetFirstPageNumber(volume) else 'Enable')()
        getattr(self._view.ForwardButton, 'Disable' if self._currentPage >= self._model.GetTotalPages(volume) else 'Enable')()
        getattr(self._view.CompareComboBox, 'Disable' if self._currentPage == 0 else 'Enable')()

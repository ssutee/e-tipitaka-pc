import wx
import constants, utils

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

    def Close(self):
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def Forward(self):
        self._currentPage += 1
        self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))
        
    def Backward(self):
        self._currentPage -= 1
        self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))

    def HandleBookSelection(self, event):
        if isinstance(event, wx.TreeEvent):
            volume, page, section = self._view.BookList.GetItemPyData(event.GetItem())
            self.OpenBook(volume, page, section if section is not None else self._model.GetSection(volume, page))
        elif isinstance(event, wx.CommandEvent):
            self.OpenBook(event.GetSelection()+1, self._model.GetFirstPageNumber(event.GetSelection()+1))
            
    def JumpToPage(self, page, code=None):
        page = page if page > 0 and page <= self._model.GetTotalPages(self._currentVolume) else self._model.GetFirstPageNumber(self._currentVolume)
        self.OpenBook(self._currentVolume, page, self._model.GetSection(self._currentVolume, page))
        
    def JumpToItem(self, item):
        page, sub = 0, 0
        try:
            if len(item.split('.')) == 2:
                item, sub = map(int, item.split('.'))
            elif len(item.split('.')) == 1:
                item, sub = int(item), 1
        except ValueError, e:
            pass
        if self._view.CheckBox.IsChecked():
            page = int(constants.MAP_MC_TO_SIAM['v%d-%d-i%d'%(self._currentVolume, sub, item)])
        else:
            try:
                page = self._model.ConvertItemToPage(self._currentVolume, item, sub)
            except ValueError, e:
                pass
        self.JumpToPage(page)

    def _ToggleButtons(self, volume):
        getattr(self._view.BackwardButton, 'Disable' if self._currentPage <= self._model.GetFirstPageNumber(volume) else 'Enable')()
        getattr(self._view.ForwardButton, 'Disable' if self._currentPage >= self._model.GetTotalPages(volume) else 'Enable')()
        getattr(self._view.CompareComboBox, 'Disable' if self._currentPage == 0 else 'Enable')()

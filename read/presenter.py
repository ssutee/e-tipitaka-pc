import wx
import constants, utils

class Presenter(object):
    def __init__(self, model, view, interactor, code):
        self._code = code
        self._model = model
        self._delegate = None
        self._view = view
        self._view.DataSource = self
        self._view.SetTitle(self._model.GetTitle())
        self._view.Start()
        interactor.Install(self, view)     
        self._currentPage = 0
        self._currentVolume = 0
        self._currentSection = None

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
        self._ToggleButtons(volume)

        self._currentVolume, self._currentSection = volume, section
        self._currentPage = self._model.MinimumPage if self._currentPage < self._model.MinimumPage else page

        self._view.SetTitles(*self._model.GetTitles(volume, section))
        self._view.SetPageNumber(page if page > 0 else None)
        self._view.SetItemNumber(*self._model.GetItems(volume, page))

        self._view.SetText(self._model.GetPage(volume, page))

    def Close(self):
        if hasattr(self._delegate, 'OnReadWindowClose'):
            self._delegate.OnReadWindowClose(self._code)
            
    def GetBookListItems(self):
        return self._model.GetBookListItems()
        
    def GetCompareChoices(self):
        return self._model.GetCompareChoices()

    def Forward(self):
        self._currentPage += 1
        self.OpenBook(self._currentVolume, self._currentPage)
        
    def Backward(self):
        self._currentPage -= 1
        self.OpenBook(self._currentVolume, self._currentPage)

    def HandleBookSelection(self, event):
        print event

    def _ToggleButtons(self, volume):
        if self._currentPage <= self._model.MinimumPage:
            self._view.BackwardButton.Disable()
        else:
            self._view.BackwardButton.Enable()

        if self._currentPage >= self._model.GetTotalPages(volume):
            self._view.ForwardButton.Disable()
        else:
            self._view.ForwardButton.Enable()        

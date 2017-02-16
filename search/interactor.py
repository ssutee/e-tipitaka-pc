import wx
import constants

class Interactor(object):
    def Install(self, presenter, view):
        self.Presenter = presenter
        self.View = view
        
        self.View.Bind(wx.EVT_CLOSE, self.OnFrameClose)
        
        self.View.TopBar.AboutButton.Bind(wx.EVT_BUTTON, self.OnAboutButtonClick)
        self.View.TopBar.SearchButton.Bind(wx.EVT_BUTTON, self.OnSearchButtonClick)
        self.View.TopBar.FontsButton.Bind(wx.EVT_BUTTON, self.OnFontsButtonClick)
        self.View.TopBar.ReadButton.Bind(wx.EVT_BUTTON, self.OnReadButtonClick)
        self.View.TopBar.SearchCtrl.Bind(wx.EVT_TEXT, self.OnSearchCtrlTextChange)

        self.View.TopBar.LanguagesComboBox.Bind(wx.EVT_COMBOBOX, self.OnLanguagesComboBoxSelect)
        self.View.ThemeComboBox.Bind(wx.EVT_COMBOBOX, self.OnThemeComboBoxSelect)
        
        self.View.ForwardButton.Bind(wx.EVT_BUTTON, self.OnForwardButtonClick)
        self.View.BackwardButton.Bind(wx.EVT_BUTTON, self.OnBackwardButtonClick)
        self.View.ExportButton.Bind(wx.EVT_BUTTON, self.OnExportButtonClick)
        self.View.ImportButton.Bind(wx.EVT_BUTTON, self.OnImportButtonClick)
        
        self.View.VolumesRadio.Bind(wx.EVT_RADIOBOX, self.OnVolumesRadioSelect)
        self.View.SortingRadioBox.Bind(wx.EVT_RADIOBOX, self.OnSortingRadioBoxSelect)
        self.View.FilterCtrl.Bind(wx.EVT_TEXT, self.OnFilterCtrlText)
        self.View.FilterCtrl.Bind(wx.EVT_TEXT_ENTER, self.OnFilterCtrlText)
        self.View.DeleteButton.Bind(wx.EVT_BUTTON, self.OnDeleteButtonClick)
        self.View.DeleteButton.Bind(wx.EVT_UPDATE_UI, self.OnUpdateDeleteButton)
        
        self.View.NikhahitButton.Bind(wx.EVT_BUTTON, self.OnNikhahitButtonClick)
        self.View.ThothanButton.Bind(wx.EVT_BUTTON, self.OnThothanButtonClick)
        self.View.YoyingButton.Bind(wx.EVT_BUTTON, self.OnYoyingButtonClick)
        
        self.View.NotesButton.Bind(wx.EVT_BUTTON, self.OnNotesButtonClick)
        self.View.StarButton.Bind(wx.EVT_BUTTON, self.OnStarButtonClick)
        
        self.View.PaliDictButton.Bind(wx.EVT_BUTTON, self.OnPaliDictButtonClick)
        self.View.ThaiDictButton.Bind(wx.EVT_BUTTON, self.OnThaiDictButtonClick)
        self.View.EnglishDictButton.Bind(wx.EVT_BUTTON, self.OnEnglishDictButtonClick)
        self.View.SearchAndCompareButton.Bind(wx.EVT_BUTTON, self.OnSearchAndCompareButtonClick)
        
        self.View.TopBar.CheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckBoxChange)
        
        self.View.HistoryList.Bind(wx.EVT_LISTBOX, self.OnHistoryListSelect)
        
    def OnAboutButtonClick(self, event):
        self.Presenter.ShowAboutDialog()

    def OnSearchButtonClick(self, event):
        self.Presenter.Search()

    def OnFrameClose(self, event):
        if self.Presenter.CanBeClosed:
            event.Skip()
        
    def OnLanguagesComboBoxSelect(self, event):
        self.Presenter.SelectLanguage(event.GetSelection())

    def OnThemeComboBoxSelect(self, event):
        self.Presenter.SelectTheme(event.GetSelection())

    def OnForwardButtonClick(self, event):
        self.Presenter.NextPagination()
        
    def OnBackwardButtonClick(self, event):
        self.Presenter.PreviousPagination()
        
    def OnVolumesRadioSelect(self, event):
        self.Presenter.SelectVolumes(event.GetSelection())

    def OnFontsButtonClick(self, event):
        self.Presenter.ShowFontDialog()
        
    def OnReadButtonClick(self, event):
        self.Presenter.OpenBook()
        
    def OnCheckBoxChange(self, event):
        self.Presenter.SetOpenNewWindow(event.GetSelection() == 1)
        
    def OnHistoryListSelect(self, event):
        self.Presenter.ReloadHistory(event.GetSelection())
        
    def OnExportButtonClick(self, event):
        self.Presenter.ExportData()
        
    def OnImportButtonClick(self, event):
        self.Presenter.ImportData()

    def OnNikhahitButtonClick(self, event):
        self.Presenter.InputSpecialCharacter(constants.NIKHAHIT_CHAR)

    def OnThothanButtonClick(self, event):
        self.Presenter.InputSpecialCharacter(constants.THOTHAN_CHAR)
        
    def OnYoyingButtonClick(self, event):
        self.Presenter.InputSpecialCharacter(constants.YOYING_CHAR)
        
    def OnSortingRadioBoxSelect(self, event):
        self.Presenter.SortHistoryList(event.GetSelection())
        
    def OnFilterCtrlText(self, event):
        self.Presenter.FilterHistoryList(self.View.FilterCtrl.GetValue())
        
    def OnDeleteButtonClick(self, event):
        self.Presenter.DeleteSelectedHistoryItem()
        
    def OnUpdateDeleteButton(self, event):
        event.Enable(self.View.HistoryList.GetSelection() > -1)
        
    def OnSearchCtrlTextChange(self, event):
        self.Presenter.ShowInputText(self.View.TopBar.SearchCtrl.GetValue())
        
    def OnStarButtonClick(self, event):
        x,y = self.View.StarButton.GetPosition()
        w,h = self.View.StarButton.GetSize()
        self.Presenter.ShowBookmarkPopup(x, y+h+5)    
        
    def OnNotesButtonClick(self, event):
        self.Presenter.ShowNotesManager()

    def OnPaliDictButtonClick(self, event):
        self.Presenter.OpenPaliDict()
        
    def OnThaiDictButtonClick(self, event):
        self.Presenter.OpenThaiDict()

    def OnEnglishDictButtonClick(self, event):
        self.Presenter.OpenEnglishDict()

    def OnSearchAndCompareButtonClick(self, event):
        self.Presenter.OpenSearchAndCompareDialog()
        

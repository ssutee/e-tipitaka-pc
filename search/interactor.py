import wx

class Interactor(object):
    def Install(self, presenter, view):
        self.Presenter = presenter
        self.View = view
        
        self.View.Bind(wx.EVT_CLOSE, self.OnFrameClose)
        
        self.View.TopBar.AboutButton.Bind(wx.EVT_BUTTON, self.OnAboutButtonClick)
        self.View.TopBar.SearchButton.Bind(wx.EVT_BUTTON, self.OnSearchButtonClick)
        self.View.TopBar.FontsButton.Bind(wx.EVT_BUTTON, self.OnFontsButtonClick)
        self.View.TopBar.ReadButton.Bind(wx.EVT_BUTTON, self.OnReadButtonClick)
        
        self.View.TopBar.LanguagesComboBox.Bind(wx.EVT_COMBOBOX, self.OnLanguagesComboBoxSelect)
        
        self.View.ForwardButton.Bind(wx.EVT_BUTTON, self.OnForwardButtonClick)
        self.View.BackwardButton.Bind(wx.EVT_BUTTON, self.OnBackwardButtonClick)
        self.View.ExportButton.Bind(wx.EVT_BUTTON, self.OnExportButtonClick)
        self.View.ImportButton.Bind(wx.EVT_BUTTON, self.OnImportButtonClick)
        
        self.View.VolumesRadio.Bind(wx.EVT_RADIOBOX, self.OnVolumesRadioSelect)
        
        self.View.TopBar.CheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckBoxChange)
        
        self.View.HistoryList.Bind(wx.EVT_LISTBOX, self.OnHistoryListSelect)
        
    def OnAboutButtonClick(self, event):
        self.Presenter.ShowAboutDialog()

    def OnSearchButtonClick(self, event):
        self.Presenter.Search()

    def OnFrameClose(self, event):
        self.Presenter.Close()
        event.Skip()
        
    def OnLanguagesComboBoxSelect(self, event):
        self.Presenter.SelectLanguage(event.GetSelection())

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


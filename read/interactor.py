import wx
import wx.richtext as rt
import constants

class Interactor(object):

    def Install(self, presenter, view):
        self.Presenter = presenter
        self.View = view
        
        self.View.Bind(wx.EVT_CLOSE, self.OnClose)
        
        self.View.ForwardButton.Bind(wx.EVT_BUTTON, self.OnForwardButtonClick)
        self.View.BackwardButton.Bind(wx.EVT_BUTTON, self.OnBackwordButtonClick)
        self.View.BookListButton.Bind(wx.EVT_BUTTON, self.OnBookListButtonClick)
        self.View.FontsButton.Bind(wx.EVT_BUTTON, self.OnFontsButtonClick)
        self.View.BookFontsButton.Bind(wx.EVT_BUTTON, self.OnBookFontsButtonClick)
        self.View.IncreaseFontButton.Bind(wx.EVT_BUTTON, self.OnIncreaseFontButtonClick)
        self.View.DecreaseFontButton.Bind(wx.EVT_BUTTON, self.OnDecreaseFontButtonClick)
        self.View.StarButton.Bind(wx.EVT_BUTTON, self.OnStarButtonClick)
        self.View.SearchButton.Bind(wx.EVT_BUTTON, self.OnSearchButtonClick)
        self.View.PrintButton.Bind(wx.EVT_BUTTON, self.OnPrintButtonClick)
        self.View.SaveButton.Bind(wx.EVT_BUTTON, self.OnSaveButtonClick)
        self.View.PaliDictButton.Bind(wx.EVT_BUTTON, self.OnPaliDictButtonClick)
        self.View.ThaiDictButton.Bind(wx.EVT_BUTTON, self.OnThaiDictButtonClick)
        self.View.EnglishDictButton.Bind(wx.EVT_BUTTON, self.OnEnglishDictButtonClick)

        self.View.NotesButton.Bind(wx.EVT_BUTTON, self.OnNotesButtonClick)
        self.View.MarkButton.Bind(wx.EVT_BUTTON, self.OnMarkButtonClick)
    
        if isinstance(self.View.BookList, wx.ListBox):
            self.View.BookList.Bind(wx.EVT_LISTBOX, self.OnBookListSelect)
        elif isinstance(self.View.BookList, wx.TreeCtrl):
            self.View.BookList.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnBookListSelect)
            
        self.View.InputPage.Bind(wx.EVT_TEXT_ENTER, self.OnInputPageEnter)
        self.View.InputPage.Bind(wx.EVT_TEXT, self.OnInputPageEnter)        
        self.View.InputItem.Bind(wx.EVT_TEXT_ENTER, self.OnInputItemEnter)
        self.View.InputItem.Bind(wx.EVT_TEXT, self.OnInputItemEnter)
        
        self.View.CompareComboBox.Bind(wx.EVT_COMBOBOX, self.OnCompareComboBoxSelect)
        self.View.ThemeComboBox.Bind(wx.EVT_COMBOBOX, self.OnThemeComboBoxSelect)            
            
    def OnClose(self, event):
        self.Presenter.Close()
        event.Skip()

    def OnForwardButtonClick(self, event):
        self.Presenter.Forward()
        
    def OnBackwordButtonClick(self, event):
        self.Presenter.Backward()
        
    def OnFontsButtonClick(self, event):
        self.Presenter.ShowFontDialog()

    def OnBookFontsButtonClick(self, event):
        self.Presenter.ShowFontDialog(constants.BOOK_FONT)
        
    def OnIncreaseFontButtonClick(self, event):
        self.Presenter.IncreaseFontSize()
        
    def OnDecreaseFontButtonClick(self, event):
        self.Presenter.DecreaseFontSize()
        
    def OnBookListButtonClick(self, event):
        self.Presenter.ToggleBookList()
        
    def OnBookListSelect(self, event):
        self.Presenter.HandleBookSelection(event)
        
    def OnStarButtonClick(self, event):
        x,y = self.View.StarButton.GetPosition()
        w,h = self.View.StarButton.GetSize()
        self.Presenter.ShowBookmarkPopup(x+280, y+h+5)    
        
    def OnSearchButtonClick(self, event):
        self.Presenter.SearchSelection()   
        
    def OnPrintButtonClick(self, event):
        self.Presenter.ShowPrintDialog()
        
    def OnSaveButtonClick(self, event):
        self.Presenter.ShowSaveDialog()
        
    def OnPaliDictButtonClick(self, event):
        self.Presenter.OpenPaliDict()

    def OnThaiDictButtonClick(self, event):
        self.Presenter.OpenThaiDict()

    def OnEnglishDictButtonClick(self, event):
        self.Presenter.OpenEnglishDict()
        
    def OnNotesButtonClick(self, event):
        self.Presenter.ShowNotesManager()

    def OnMarkButtonClick(self, event):
        self.Presenter.ShowMarkManager()

    def OnInputPageEnter(self, event):
        try:
            self.Presenter.JumpToPage(int(self.View.InputPage.GetValue()))
        except ValueError,e:
            self.Presenter.JumpToPage(0)
                
    def OnInputItemEnter(self, event):        
        self.Presenter.JumpToItem(self.View.InputItem.GetValue())
            
    def OnCompareComboBoxSelect(self, event):
        self.Presenter.CompareTo(event.GetSelection())
        
    def OnToggleNoteButtonClick(self, event):
        self.Presenter.ToggleNotePanel()
        
    def OnThemeComboBoxSelect(self, event):
        self.Presenter.SelectTheme(event.GetSelection())

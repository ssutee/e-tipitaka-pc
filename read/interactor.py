import wx
import wx.richtext as rt

class Interactor(object):

    def Install(self, presenter, view):
        self.Presenter = presenter
        self.View = view
        
        self.View.Bind(wx.EVT_CLOSE, self.OnClose)
        
        self.View.ForwardButton.Bind(wx.EVT_BUTTON, self.OnForwardButtonClick)
        self.View.BackwardButton.Bind(wx.EVT_BUTTON, self.OnBackwordButtonClick)
        self.View.BookListButton.Bind(wx.EVT_BUTTON, self.OnBookListButtonClick)
        self.View.FontsButton.Bind(wx.EVT_BUTTON, self.OnFontsButtonClick)
        self.View.IncreaseFontButton.Bind(wx.EVT_BUTTON, self.OnIncreaseFontButtonClick)
        self.View.DecreaseFontButton.Bind(wx.EVT_BUTTON, self.OnDecreaseFontButtonClick)
        self.View.StarButton.Bind(wx.EVT_BUTTON, self.OnStarButtonClick)
        self.View.SearchButton.Bind(wx.EVT_BUTTON, self.OnSearchButtonClick)
        self.View.PrintButton.Bind(wx.EVT_BUTTON, self.OnPrintButtonClick)
        self.View.SaveButton.Bind(wx.EVT_BUTTON, self.OnSaveButtonClick)
        self.View.DictButton.Bind(wx.EVT_BUTTON, self.OnDictButtonClick)
    
        if isinstance(self.View.BookList, wx.ListBox):
            self.View.BookList.Bind(wx.EVT_LISTBOX, self.OnBookListSelect)
        elif isinstance(self.View.BookList, wx.TreeCtrl):
            self.View.BookList.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnBookListSelect)
            
        self.View.InputPage.Bind(wx.EVT_TEXT_ENTER, self.OnInputPageEnter)
        self.View.InputPage.Bind(wx.EVT_TEXT, self.OnInputPageEnter)        
        self.View.InputItem.Bind(wx.EVT_TEXT_ENTER, self.OnInputItemEnter)
        self.View.InputItem.Bind(wx.EVT_TEXT, self.OnInputItemEnter)
        
        self.View.CompareComboBox.Bind(wx.EVT_COMBOBOX, self.OnCompareComboBoxSelect)

        self._DoBind(self.View.NotePanel.SaveItem, self.OnSave, self.OnUpdateSave)
                
        self._DoBind(self.View.NotePanel.BoldItem, self.OnBold, self.OnUpdateBold)
        self._DoBind(self.View.NotePanel.ItalicItem, self.OnItalic, self.OnUpdateItalic)
        self._DoBind(self.View.NotePanel.UnderlineItem, self.OnUnderline, self.OnUpdateUnderline)

        self._DoBind(self.View.NotePanel.AlignLeftItem, self.OnAlignLeft, self.OnUpdateAlignLeft)
        self._DoBind(self.View.NotePanel.AlignRightItem, self.OnAlignRight, self.OnUpdateAlignRight)
        self._DoBind(self.View.NotePanel.CenterItem, self.OnCenter, self.OnUpdateCenter)
        
        self._DoBind(self.View.NotePanel.IndentLessItem, self.OnIndentLess)
        self._DoBind(self.View.NotePanel.IndentMoreItem, self.OnIndentMore)

        self._DoBind(self.View.NotePanel.FontItem, self.OnFont)
        self._DoBind(self.View.NotePanel.FontColorItem, self.OnFontColor)

    def _DoBind(self, item, handler, updateUI=None):
        self.View.Bind(wx.EVT_TOOL, handler, item)
        if updateUI is not None:
            self.View.Bind(wx.EVT_UPDATE_UI, updateUI, item)

    def OnSave(self, event):
        self.Presenter.SaveNoteText()
        
    def OnUpdateSave(self, event):
        event.Enable(self.View.NotePanel.NoteTextCtrl.IsModified())

    def OnBold(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyBoldToSelection()

    def OnUpdateBold(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionBold())

    def OnItalic(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyItalicToSelection()

    def OnUpdateItalic(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionItalics())

    def OnUnderline(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyUnderlineToSelection()

    def OnUpdateUnderline(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionUnderlined())

    def OnAlignLeft(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(rt.TEXT_ALIGNMENT_LEFT)

    def OnUpdateAlignLeft(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionAligned(rt.TEXT_ALIGNMENT_LEFT))

    def OnAlignRight(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(rt.TEXT_ALIGNMENT_RIGHT)

    def OnUpdateAlignRight(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionAligned(rt.TEXT_ALIGNMENT_RIGHT))

    def OnCenter(self, event):
        self.View.NotePanel.NoteTextCtrl.ApplyAlignmentToSelection(rt.TEXT_ALIGNMENT_CENTRE)

    def OnUpdateCenter(self, event):
        event.Check(self.View.NotePanel.NoteTextCtrl.IsSelectionAligned(rt.TEXT_ALIGNMENT_CENTRE))

    def OnIndentLess(self, event):
        self.Presenter.IndentLessNoteText()

    def OnIndentMore(self, event):
        self.Presenter.IndentMoreNoteText()

    def OnFont(self, event):
        self.Presenter.ApplyFontToNoteText()

    def OnFontColor(self, event):
        self.Presenter.ApplyFontColorToNoteText()
            
    def OnClose(self, event):
        self.Presenter.Close()
        event.Skip()

    def OnForwardButtonClick(self, event):
        self.Presenter.Forward()
        
    def OnBackwordButtonClick(self, event):
        self.Presenter.Backward()
        
    def OnFontsButtonClick(self, event):
        self.Presenter.ShowFontDialog()
        
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
        
    def OnDictButtonClick(self, event):
        self.Presenter.OpenDict()

    def OnInputPageEnter(self, event):
        try:
            self.Presenter.JumpToPage(int(self.View.InputPage.GetValue()))
        except ValueError,e:
            self.Presenter.JumpToPage(0)
                
    def OnInputItemEnter(self, event):        
        self.Presenter.JumpToItem(self.View.InputItem.GetValue())
            
    def OnCompareComboBoxSelect(self, event):
        self.Presenter.CompareTo(event.GetSelection())

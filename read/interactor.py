import wx

class Interactor(object):

    def Install(self, presenter, view):
        self.Presenter = presenter
        self.View = view
        
        self.View.Bind(wx.EVT_CLOSE, self.OnClose)
        
        self.View.ForwardButton.Bind(wx.EVT_BUTTON, self.OnForwardButtonClick)
        self.View.BackwardButton.Bind(wx.EVT_BUTTON, self.OnBackwordButtonClick)
        
        if isinstance(self.View.BookList, wx.ListBox):
            self.View.BookList.Bind(wx.EVT_LISTBOX, self.OnBookListSelect)
        elif isinstance(self.View.BookList, wx.TreeCtrl):
            self.View.BookList.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnBookListSelect)
            
        self.View.InputPage.Bind(wx.EVT_TEXT_ENTER, self.OnInputPageEnter)
        self.View.InputPage.Bind(wx.EVT_TEXT, self.OnInputPageEnter)        
        self.View.InputItem.Bind(wx.EVT_TEXT_ENTER, self.OnInputItemEnter)
        self.View.InputItem.Bind(wx.EVT_TEXT, self.OnInputItemEnter)
                
    def OnClose(self, event):
        self.Presenter.Close()
        event.Skip()

    def OnForwardButtonClick(self, event):
        self.Presenter.Forward()
        
    def OnBackwordButtonClick(self, event):
        self.Presenter.Backward()
        
    def OnBookListSelect(self, event):
        self.Presenter.HandleBookSelection(event)

    def OnInputPageEnter(self, event):
        try:
            self.Presenter.JumpToPage(int(self.View.InputPage.GetValue()))
        except ValueError,e:
            self.Presenter.JumpToPage(0)
        
    def OnInputItemEnter(self, event):
        self.Presenter.JumpToItem(self.View.InputItem.GetValue())
            
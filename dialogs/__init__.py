import wx
import sys, os
import i18n
_ = i18n.language.ugettext

import settings

class VolumesDialog(wx.Dialog):
    def __init__(self, parent, volumes, dataSource):        
        wx.Dialog.__init__(self, parent, wx.ID_ANY, _('Please select volumes'))
        
        self._dataSource = dataSource
        
        w,h = wx.GetDisplaySize()        
        self.checklist = wx.CheckListBox(self, wx.ID_ANY, choices=self._dataSource.GetBookNames(), size=(-1, 600))
        for volume in volumes:
            self.checklist.Check(volume, True)

        self.checklist.Bind(wx.EVT_CHECKLISTBOX, self.OnCheckListBox)
            
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        self.btnFirst = wx.Button(self, -1, _('Section 1'))
        self.btnSecond = wx.Button(self, -1, _('Section 2'))
        self.btnThird = wx.Button(self, -1, _('Section 3'))
        self.btnSelAll = wx.Button(self, -1, _('Select all'))
        self.btnDelAll = wx.Button(self, -1, _('Clear'))

        self.btnFirst.Bind(wx.EVT_BUTTON, self.OnClickFirst)
        self.btnSecond.Bind(wx.EVT_BUTTON, self.OnClickSecond)
        self.btnThird.Bind(wx.EVT_BUTTON, self.OnClickThird)
        self.btnSelAll.Bind(wx.EVT_BUTTON, self.OnClickSelAll)
        self.btnDelAll.Bind(wx.EVT_BUTTON, self.OnClickDelAll)

        self.btnOk = wx.Button(self, wx.ID_OK, _('OK'))
        self.btnOk.SetDefault()
        self.btnCancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))

        if len(volumes) == 0:
            self.btnOk.Disable()
        
        leftSizer.Add(self.btnFirst, flag=wx.EXPAND)
        leftSizer.Add(self.btnSecond, flag=wx.EXPAND)
        leftSizer.Add(self.btnThird, flag=wx.EXPAND)
        leftSizer.Add((-1,30), flag=wx.EXPAND)
        leftSizer.Add(self.btnSelAll, flag=wx.EXPAND)
        leftSizer.Add(self.btnDelAll, flag=wx.EXPAND)
        leftSizer.Add((-1,-1), 1, flag=wx.EXPAND)
        leftSizer.Add(self.btnOk, flag=wx.EXPAND)
        leftSizer.Add(self.btnCancel, flag=wx.EXPAND)

        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(leftSizer, flag=wx.EXPAND)
        mainSizer.Add(self.checklist, 1, flag=wx.EXPAND)
        self.SetSizer(mainSizer)

        self.Fit()

    def GetCheckedVolumes(self):
        results = ()
        for i in range(self.checklist.GetCount()):
            if self.checklist.IsChecked(i):
                results += (i,)
        return results

    def OnClickFirst(self, event):        
        for i in range(self._dataSource.GetSectionBoundary(0)):
            self.checklist.Check(i, True)
        self.btnOk.Enable()
        
    def OnClickSecond(self, event):
        for i in range(self._dataSource.GetSectionBoundary(0), self._dataSource.GetSectionBoundary(1)):
            self.checklist.Check(i,True)
        self.btnOk.Enable()
        
    def OnClickThird(self, event):
        for i in range(self._dataSource.GetSectionBoundary(1), self._dataSource.GetSectionBoundary(2)):
            self.checklist.Check(i,True)
        self.btnOk.Enable()
        
    def OnClickSelAll(self, event):
        for i in range(self._dataSource.GetSectionBoundary(2)):
            self.checklist.Check(i, True)
        self.btnOk.Enable()
        
    def OnClickDelAll(self, event):
        for i in range(self._dataSource.GetSectionBoundary(2)):
            self.checklist.Check(i, False)
        self.btnOk.Disable()    
        
    def OnCheckListBox(self, event):
        if len(self.GetCheckedVolumes()) == 0:
            self.btnOk.Disable()
        else:
            self.btnOk.Enable()

class AboutDialog(wx.Dialog):
    def __init__(self, parent, *args, **kwargs):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, _('About E-Tipitaka'))
        
        label1 = wx.StaticText(self, wx.ID_ANY, 
            _('E-Tipitaka %s - developed by Sutee Sudprasert Copyright (C) 2010\n written by Python 2.7.3 and wxPython 2.8 (unicode)') % (settings.VERSION))
        label2 = wx.StaticText(self, wx.ID_ANY, 
            _('This program is free software distributed under Apache License, Version 2.0'))
        label3 = wx.StaticText(self, wx.ID_ANY, 
            _('If you have any suggestion or comment, please send to <etipitaka@gmail.com>'))

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer.Add(label3, flag=wx.ALIGN_CENTER_VERTICAL)
        bottomSizer.Add((20,20), 1, wx.EXPAND)
        bottomSizer.Add(wx.Button(self, wx.ID_OK, _('OK')))
                
        mainSizer.Add((-1,10), 1, flag=wx.EXPAND)
        mainSizer.Add(label1,0, wx.EXPAND|wx.ALL, 10)
        mainSizer.Add(label2,0, wx.EXPAND|wx.ALL, 10)                
        mainSizer.Add(bottomSizer, 0, wx.EXPAND|wx.ALL, 10)
        mainSizer.Add((-1,10), 1, flag=wx.EXPAND)        
        self.SetSizer(mainSizer)
        self.Fit()

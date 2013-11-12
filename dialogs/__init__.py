#-*- coding:utf-8 -*-

import wx
from wx.lib.combotreebox import ComboTreeBox
import wx.richtext as rt
import sys, os
import i18n
_ = i18n.language.ugettext

import settings
import read.model

from pony.orm import db_session

class DataXferPagesValidator(wx.PyValidator):
    def __init__(self, data, key):
        wx.PyValidator.__init__(self)
        self.data = data
        self.key = key
        self.Bind(wx.EVT_CHAR, self.OnChar)
        
    def Clone(self):
        return DataXferPagesValidator(self.data, self.key)
        
    def Validate(self, win):
        combo = self.GetWindow()
        text = combo.GetValue()
        if len(text.strip()) == 0:
            wx.MessageBox(u'ช่องนี้ไม่สามารถเว้นว่างได้',u'พบข้อผิดพลาด')
            combo.SetBackgroundColour('pink')
            combo.Refresh()
            return False
        else:
            combo.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
            combo.Refresh()
            return True
        
    def TransferToWindow(self):
        combo = self.GetWindow()
        combo.SetSelection(self.data.get(self.key,0))
        return True
        
    def TransferFromWindow(self):
        combo = self.GetWindow()
        self.data[self.key] = int(combo.GetValue())-1
        return True
        
    def OnChar(self, event):
        code = event.GetKeyCode()
        combo = self.GetWindow()
        text = combo.GetValue()
        count = combo.GetCount()
        
        if (code < 48 or code > 57) and code != 8:
            return
            
        if (code >= 48 and code <= 57) and int(text + chr(code)) > count:
            return

        if text == '' and code == 48:
            return
            
        event.Skip()

class NoteManagerDialog(wx.Dialog):
    def __init__(self, parent, code):
        super(NoteManagerDialog, self).__init__(parent, wx.ID_ANY, u'ค้นหาบันทึกข้อความเพิ่มเติม', size=(600,500), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self._result = None
        self._code = code
        self.Center()        
        self.SetBackgroundColour('white')
        self._noteTextCtrl = rt.RichTextCtrl(self, style=wx.VSCROLL|wx.HSCROLL)
        self._noteTextCtrl.SetEditable(False)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        self._searchCtrl = wx.SearchCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self._searchCtrl.SetFocus()
        self._searchCtrl.Bind(wx.EVT_TEXT, self.OnSearchCtrlTextEnter)
        self._readButton = wx.Button(self, wx.ID_ANY, u'อ่าน')
        self._readButton.Bind(wx.EVT_UPDATE_UI, self.OnUpdateReadButton)
        self._readButton.Bind(wx.EVT_BUTTON, self.OnReadButtonClick)
        
        with db_session:
            items = read.model.Model.GetNoteListItems(self._code)
            self._noteListBox = wx.ListBox(self, wx.ID_ANY, choices=items, style=wx.LB_SINGLE|wx.LB_NEEDED_SB)
            self._noteListBox.Bind(wx.EVT_LISTBOX, self.OnNoteListBoxSelect)
            self._noteListBox.Bind(wx.EVT_LISTBOX_DCLICK, self.OnNoteListBoxDoubleClick)

        leftSizer.Add(self._searchCtrl, 0, wx.EXPAND|wx.ALL, 5)
        leftSizer.Add(self._noteListBox, 1, wx.EXPAND|wx.ALL, 5)
        leftSizer.Add(self._readButton, 0, wx.CENTER|wx.BOTTOM, 10)
        sizer.Add(leftSizer, 2, wx.EXPAND)
        sizer.Add(self._noteTextCtrl, 3, wx.EXPAND|wx.ALL, 5)        
        self.SetSizer(sizer)
        
    def OnNoteListBoxSelect(self, event):
        text = self._searchCtrl.GetValue()
        with db_session:
            note = list(read.model.Model.GetNotes(self._code, text))[event.GetSelection()]
            self._noteTextCtrl.LoadFile(note.filename, rt.RICHTEXT_TYPE_XML)

    def OnSearchCtrlTextEnter(self, event):
        with db_session:
            items = read.model.Model.GetNoteListItems(self._code, self._searchCtrl.GetValue())
            self._noteListBox.SetItems(items)
            self._noteTextCtrl.SetEditable(True)
            self._noteTextCtrl.SelectAll()
            self._noteTextCtrl.DeleteSelection()        
            self._noteTextCtrl.EndAllStyles()   
            self._noteTextCtrl.SetEditable(False)  
            
    def OnUpdateReadButton(self, event):
        event.Enable(self._noteListBox.GetSelection() > -1)       
        
    def OnReadButtonClick(self, event):
        self._OpenNote(self._noteListBox.GetSelection())
            
    def OnNoteListBoxDoubleClick(self, event):
        self._OpenNote(event.GetSelection())
            
    def _OpenNote(self, selection):
        if selection == -1: return
        
        with db_session:
            note = list(read.model.Model.GetNotes(self._code, self._searchCtrl.GetValue()))[self._noteListBox.GetSelection()]
            self._result = note.volume, note.page
            self.EndModal(wx.ID_OK)
    
    @property
    def Result(self):
        return self._result

class PageRangeDialog(wx.Dialog):
    def __init__(self, parent, title, msg1, msg2, num, data):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, size=(350,200))
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        s1 = wx.BoxSizer(wx.HORIZONTAL)
        s1.Add((20,-1), 1, flag=wx.EXPAND)
        s1.Add(wx.StaticText(self, -1, u'%s'%(msg1), style=wx.ALIGN_CENTER))
        s1.Add((20,-1), 1, flag=wx.EXPAND)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add((20,-1), 1, flag=wx.EXPAND)
        s2.Add(wx.StaticText(self, -1, u'%s'%(msg2), style=wx.ALIGN_CENTER))
        s2.Add((20,-1), 1, flag=wx.EXPAND)

        s3 = wx.BoxSizer(wx.HORIZONTAL)
        s3.Add((20,-1), 1, flag=wx.EXPAND)
        s3.Add(wx.StaticText(self, wx.ID_ANY, u'หน้า', style=wx.ALIGN_CENTER))
        s3.Add((20,-1),1, flag=wx.EXPAND)
        
        rangeSizer = wx.BoxSizer(wx.HORIZONTAL)

        fromChoice = wx.ComboBox(self, wx.ID_ANY, size=(70,-1),
                                 choices=[u'%d'%(x) for x in range(1,num+1)], validator=DataXferPagesValidator(data,'from'))
        toChoice = wx.ComboBox(self, wx.ID_ANY, size=(70,-1),
                               choices=[u'%d'%(x) for x in range(1,num+1)], validator=DataXferPagesValidator(data,'to'))
        
        rangeSizer.Add((20,-1), 1, flag=wx.EXPAND)
        rangeSizer.Add(fromChoice)
        rangeSizer.Add((5,-1)) 
        rangeSizer.Add(wx.StaticText(self, wx.ID_ANY, u' ถึง ', style=wx.ALIGN_CENTER), flag=wx.ALIGN_CENTER_VERTICAL)
        rangeSizer.Add((5,-1))        
        rangeSizer.Add(toChoice)
        rangeSizer.Add((20,-1), 1, flag=wx.EXPAND)
        
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnOk = wx.Button(self, wx.ID_OK, u'ตกลง',size=(-1,-1))
        btnCancel = wx.Button(self, wx.ID_CANCEL, u'ยกเลิก', size=(-1,-1))
        btnOk.SetDefault()
        btnSizer.Add((20,-1), 1, flag=wx.EXPAND)
        btnSizer.Add(btnOk, flag=wx.EXPAND)
        btnSizer.Add((10,-1))
        btnSizer.Add(btnCancel, flag=wx.EXPAND)
        btnSizer.Add((20,-1), 1, flag=wx.EXPAND)

        mainSizer.Add((-1,10), 1, flag=wx.EXPAND)
        mainSizer.Add(s1, flag=wx.EXPAND)
        mainSizer.Add((-1,5), flag=wx.EXPAND)
        mainSizer.Add(s2, flag=wx.EXPAND)
        mainSizer.Add((-1,10),flag=wx.EXPAND)
        mainSizer.Add(s3, flag=wx.EXPAND)
        mainSizer.Add((-1,5),flag=wx.EXPAND)
        mainSizer.Add(rangeSizer, flag=wx.EXPAND)
        mainSizer.Add((-1,15),flag=wx.EXPAND)
        mainSizer.Add(btnSizer, flag=wx.EXPAND)
        mainSizer.Add((-1,10), 1, flag=wx.EXPAND)
        
        self.Center()
        self.SetSizer(mainSizer)

class BookmarkManagerDialog(wx.Dialog):
    def __init__(self, parent, items):
        wx.Dialog.__init__(self, parent, -1, u'ตัวจัดการที่คั่นหน้า', size=(600, 400))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Center()
        self._items = items
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._tree = wx.TreeCtrl(self, -1, style=wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT)

        sizer.Add(self._tree, 1, wx.EXPAND|wx.ALL, 10)        
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.CreateButton = wx.Button(self, -1, u'สร้างกลุ่ม')
        self.CreateButton.Bind(wx.EVT_BUTTON, self.OnCreateButton)
        self.DeleteButton = wx.Button(self, -1, u'ลบ')
        self.DeleteButton.Bind(wx.EVT_BUTTON, self.OnDeleteButton)
        self.MoveButton = wx.Button(self, -1, u'ย้ายกลุ่ม')
        self.MoveButton.Bind(wx.EVT_BUTTON, self.OnMoveButton)
        self.EditButton = wx.Button(self, -1, u'แก้ไข')
        self.EditButton.Bind(wx.EVT_BUTTON, self.OnEditButton)

        bottomSizer.Add((10,-1), 0)
        bottomSizer.Add(self.CreateButton, 1, wx.EXPAND)
        bottomSizer.Add(self.MoveButton, 1, wx.EXPAND)
        bottomSizer.Add(self.EditButton, 1, wx.EXPAND)        
        bottomSizer.Add(self.DeleteButton, 1, wx.EXPAND)        
        bottomSizer.Add((10,-1), 0)                
        
        sizer.Add(bottomSizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        self.SetSizer(sizer)
        self.Reload()        
        
    def OnClose(self, event):
        self._tree.DeleteAllItems()
        event.Skip()
        
    def OnEditButton(self, event):
        item = self._tree.GetPyData(self._tree.GetSelection())
        if isinstance(item ,dict):
            dialog = wx.TextEntryDialog(self, u'กรุณาป้อนชื่อกลุ่ม', u'เปลี่ยนชื่อกลุ่ม')
            dialog.SetValue(item.keys()[0])
            dialog.Center()
            if dialog.ShowModal() == wx.ID_OK:
                item[dialog.GetValue().strip()] = item.pop(item.keys()[0])
                self.Reload()
            dialog.Destroy()
        elif isinstance(item, tuple):
            dialog = wx.TextEntryDialog(self, u'กรุณาป้อนข้อมูลของคั่นหน้า', u'เปลี่ยนข้อมูลคั่นหน้า')
            dialog.SetValue(':'.join(item[2].split(':')[1:]).strip())
            dialog.Center()
            if dialog.ShowModal() == wx.ID_OK:
                container = self.FindContainer(item, self._items)
                note = item[2].split(':')[0].strip() + ' : ' + dialog.GetValue().strip()
                container.append((item[0], item[1], note))
                self.Delete(container, item)
                self.Reload()
            dialog.Destroy()
        
    def OnMoveButton(self, event):
        source = self._tree.GetPyData(self._tree.GetSelection())
        if source != None:
            dialog = BookmarkFolderDialog(self, self._items, source)
            if dialog.ShowModal() == wx.ID_OK:
                target = dialog.GetValue()
                if isinstance(target, list):
                    self.Delete(self._items, source)
                    target.append(source)
                    self.Reload()
            dialog.Destroy()
    
    def FindContainer(self, item, items):
        for i in xrange(len(items)):
            if item is items[i]:
                return items
            elif isinstance(items[i], dict):
                container = self.FindContainer(item, items[i].values()[0])
                if container != None: return container
        return None

        
    def OnCreateButton(self, event):    
        dialog = wx.TextEntryDialog(self, u'กรุณาป้อนชื่อกลุ่ม', u'สร้างกลุ่ม')
        dialog.Center()
        if dialog.ShowModal() == wx.ID_OK:
            item = self._tree.GetPyData(self._tree.GetSelection()) if self._tree.GetSelection() else None
            container = self.FindContainer(item, self._items) if item != None else self._items
            folder = dialog.GetValue().strip()
            container.append({folder:[]})
            container.sort()
            self.Reload()
        dialog.Destroy()
        
    def Delete(self, items, item):
        for i,child in enumerate(items):
            if child is item:
                del items[i]
                break;
            elif isinstance(child, dict):
                self.Delete(child.values()[0], item)
        
    def OnDeleteButton(self, event):    
        item = self._tree.GetPyData(self._tree.GetSelection())
        if item != None:
            dialog = wx.MessageDialog(self, u'คุณต้องการลบการจดจำนี้หรือไม่?' + 
                u' (ถ้าลบกลุ่ม การจดจำทั้งหมดในกลุ่มจะถูกลบไปด้วย)', u'ยืนยันการลบ', 
                wx.YES_NO | wx.ICON_INFORMATION)
            dialog.Center()
            if dialog.ShowModal() == wx.ID_YES:
                self.Delete(self._items, item)
                self.Reload()                
            dialog.Destroy()
        
    def Reload(self):

        def Load(tree, root, items):
            for item in items:
                if isinstance(item, dict):
                    folder = item.keys()[0]
                    child = tree.AppendItem(root, folder)
                    tree.SetPyData(child, item)
                    tree.SetItemImage(child, self.fldridx, wx.TreeItemIcon_Normal)
                    tree.SetItemImage(child, self.fldropenidx, wx.TreeItemIcon_Expanded)
                    Load(tree, child, item[folder])
                elif isinstance(item, tuple):
                    child = tree.AppendItem(root, item[2])
                    tree.SetPyData(child, item)
                    tree.SetItemImage(child, self.fileidx, wx.TreeItemIcon_Normal)
                    
        self._tree.DeleteAllItems()

        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz))
        self.fileidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self._tree.SetImageList(il)        
        self.il = il
        
        root = self._tree.AddRoot("root")
        self._tree.SetPyData(root, None)
        Load(self._tree, root, self._items)
        self._tree.ExpandAll()

class BookmarkFolderDialog(wx.Dialog):
    def __init__(self, parent, items, dataSource=None):
        wx.Dialog.__init__(self, parent, -1, u'เลือกกลุ่ม', size=(300, 350))
        self._dataSource = dataSource
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Center()
        self._items = items
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._tree = wx.TreeCtrl(self, -1, style=wx.TR_DEFAULT_STYLE)
        sizer.Add(self._tree, 1, wx.EXPAND|wx.ALL, 10)
        selectButton = wx.Button(self, -1, u'ตกลง')
        selectButton.Bind(wx.EVT_BUTTON, self.OnSelectButton)
        sizer.Add(selectButton, 0, wx.ALIGN_CENTER|wx.BOTTOM, 10)
        self.SetSizer(sizer)
        self.CreateTree()

    def OnSelectButton(self, event):
        self.value = self._tree.GetPyData(self._tree.GetSelection())
        self.EndModal(wx.ID_OK)

    def GetValue(self):
        return getattr(self, 'value', None)

    def CreateTree(self):
            
        def Create(tree, root, items):
            for item in items:
                if isinstance(item ,dict) and item is not self._dataSource:
                    folder = item.keys()[0]
                    child = tree.AppendItem(root, folder)
                    tree.SetPyData(child, item[folder])
                    tree.SetItemImage(child, self.fldridx, wx.TreeItemIcon_Normal)
                    tree.SetItemImage(child, self.fldropenidx, wx.TreeItemIcon_Expanded)
                    Create(tree, child, item[folder])
            
        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz))
        self._tree.SetImageList(il)        
        self.il = il
            
        root = self._tree.AddRoot(u'หลัก')
        self._tree.SetPyData(root, self._items)
        Create(self._tree, root, self._items)
        self._tree.ExpandAll()

    def OnClose(self, event):
        self._tree.DeleteAllItems()
        event.Skip()

class BookMarkDialog(wx.Dialog):
    def __init__(self, parent, items):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, u'โปรดใส่ข้อมูลของคั่นหน้า')
        self._items = items
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(wx.StaticText(self, -1, u'หมายเหตุ :', size=(70,-1), style=wx.ALIGN_RIGHT), 0, wx.ALIGN_CENTER)
        self.NoteText = wx.TextCtrl(self, -1)
        sizer1.Add(self.NoteText, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER, 8)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(wx.StaticText(self, -1, u'กลุ่ม :', size=(70,-1), style=wx.ALIGN_RIGHT), 0, wx.ALIGN_CENTER)
        self.ComboBox = self.CreateComboBox()
        sizer2.Add(self.ComboBox, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER, 8)
        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        self.CancelButton = wx.Button(self, wx.ID_CANCEL, u'ยกเลิก')
        self.SaveButton = wx.Button(self, -1, u'บันทึก')
        self.SaveButton.Bind(wx.EVT_BUTTON, self.OnSaveButton)
        sizer3.Add((-1,-1), 1, wx.EXPAND)        
        sizer3.Add(self.CancelButton, 0)
        sizer3.Add(self.SaveButton, 0)
        sizer3.Add((-1,-1), 1, wx.EXPAND)                
        mainSizer.Add(sizer1, 0, wx.EXPAND|wx.TOP, 10)
        mainSizer.Add((-1, 5), 0)
        mainSizer.Add(sizer2, 0, wx.EXPAND|wx.TOP)
        mainSizer.Add((-1,-1), 1, wx.EXPAND)
        mainSizer.Add(sizer3, 0, wx.EXPAND|wx.BOTTOM|wx.TOP, 10)
        self.SetSizer(mainSizer)
        self.Center()
        self.Fit()

    def GetValue(self):
        return getattr(self, 'value', None)

    def CreateComboBox(self):
        
        def _CreateComboBox(comboBox, root, items):
            for item in items:
                if isinstance(item, dict):
                    child = comboBox.Append(item.keys()[0], root, clientData=item.values()[0])
                    _CreateComboBox(comboBox, child, item.values()[0])
                    
        comboBox = ComboTreeBox(self, wx.CB_READONLY) 
        root = comboBox.Append(u'หลัก', clientData=self._items)
        _CreateComboBox(comboBox, root, self._items)
        comboBox.SetSelection(root)
        comboBox.GetTree().ExpandAll()       
        return comboBox
        
    def OnSaveButton(self, event):
        item = self.ComboBox.GetSelection()
        note = self.NoteText.GetValue()
        if item:
            container = self.ComboBox.GetClientData(item)
            self.value = (container, note.strip())
            self.EndModal(wx.ID_OK)


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

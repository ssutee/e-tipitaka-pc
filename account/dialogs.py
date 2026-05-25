#-*- coding:utf-8 -*-

import os
import tempfile
import threading
from datetime import datetime

import wx

from account.client import AccountError


MSGBOX_TITLE = u'E-Tipitaka — บัญชีผู้ใช้'


def _run_in_thread(work, on_success, on_error):
    """Run `work()` on a worker thread; deliver result via wx.CallAfter."""
    def _target():
        try:
            result = work()
        except AccountError as e:
            wx.CallAfter(on_error, e)
            return
        except Exception as e:
            wx.CallAfter(on_error, AccountError(0, str(e)))
            return
        wx.CallAfter(on_success, result)

    threading.Thread(target=_target, daemon=True).start()


def _show_error(parent, err):
    if err.status == 401:
        msg = u'เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่'
    elif err.status == 404:
        msg = u'ไม่พบข้อมูลสำรอง'
    elif err.status == 0:
        msg = u'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบอินเทอร์เน็ต\n\n%s' % err.message
    else:
        msg = err.message or (u'HTTP %d' % err.status)
    wx.MessageBox(msg, MSGBOX_TITLE, wx.OK | wx.ICON_ERROR, parent)


class SignUpDialog(wx.Dialog):

    def __init__(self, parent, client):
        super(SignUpDialog, self).__init__(parent, title=u'สมัครสมาชิก',
                                           size=(360, 260))
        self._client = client

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=4, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)

        self._email = wx.TextCtrl(panel)
        self._username = wx.TextCtrl(panel)
        self._password = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._confirm = wx.TextCtrl(panel, style=wx.TE_PASSWORD)

        for label, ctrl in [(u'อีเมล', self._email),
                            (u'ชื่อผู้ใช้', self._username),
                            (u'รหัสผ่าน', self._password),
                            (u'ยืนยันรหัสผ่าน', self._confirm)]:
            grid.Add(wx.StaticText(panel, label=label),
                     flag=wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        self._btnOk = wx.Button(panel, label=u'สมัครสมาชิก')
        self._btnCancel = wx.Button(panel, wx.ID_CANCEL, label=u'ยกเลิก')
        self._btnOk.Bind(wx.EVT_BUTTON, self._on_signup)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnRow.AddStretchSpacer()
        btnRow.Add(self._btnOk, 0, wx.RIGHT, 6)
        btnRow.Add(self._btnCancel, 0)

        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, evt):
        if not self._btnOk.IsEnabled():
            evt.Veto()
            return
        self.EndModal(wx.ID_CANCEL)

    def _on_signup(self, _evt):
        email = self._email.GetValue().strip()
        username = self._username.GetValue().strip()
        pw = self._password.GetValue()
        cf = self._confirm.GetValue()
        if not (email and username and pw):
            wx.MessageBox(u'ต้องระบุอีเมล ชื่อผู้ใช้ และรหัสผ่าน',
                          u'สมัครสมาชิก', wx.OK | wx.ICON_WARNING, self)
            return
        if pw != cf:
            wx.MessageBox(u'รหัสผ่านไม่ตรงกัน', u'สมัครสมาชิก',
                          wx.OK | wx.ICON_WARNING, self)
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.register(email, username, pw),
            on_success=self._on_done(email),
            on_error=self._on_err,
        )

    def _on_done(self, email):
        def _cb(_result):
            self._busy(False)
            wx.MessageBox(u'ส่งอีเมลยืนยันไปยัง %s แล้ว' % email,
                          u'สมัครสมาชิก', wx.OK | wx.ICON_INFORMATION, self)
            self.EndModal(wx.ID_OK)
        return _cb

    def _on_err(self, err):
        self._busy(False)
        _show_error(self, err)

    def _busy(self, on):
        self._btnOk.Enable(not on)
        self._btnCancel.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()


class BackupListDialog(wx.Dialog):

    def __init__(self, parent, client, presenter):
        super(BackupListDialog, self).__init__(parent, title=u'จัดการข้อมูลสำรอง',
                                               size=(560, 360))
        self._client = client
        self._presenter = presenter

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._list.InsertColumn(0, u'วันที่', width=170)
        self._list.InsertColumn(1, u'ชื่อไฟล์', width=240)
        self._list.InsertColumn(2, u'แพลตฟอร์ม', width=80)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_download)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        self._btnDownload = wx.Button(panel, label=u'ดาวน์โหลด')
        self._btnDelete = wx.Button(panel, label=u'ลบ')
        self._btnClose = wx.Button(panel, wx.ID_CLOSE, label=u'ปิด')
        self._btnDownload.Bind(wx.EVT_BUTTON, self._on_download)
        self._btnDelete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        btnRow.Add(self._btnDownload, 0, wx.RIGHT, 6)
        btnRow.Add(self._btnDelete, 0, wx.RIGHT, 6)
        btnRow.AddStretchSpacer()
        btnRow.Add(self._btnClose, 0)

        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        self._rows = []
        self._refresh()

    def _on_close(self, evt):
        if any(not b.IsEnabled() for b in (self._btnDownload, self._btnDelete, self._btnClose)):
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _refresh(self):
        self._busy(True)
        _run_in_thread(
            lambda: self._client.list_backups(),
            on_success=self._on_listed,
            on_error=self._on_err,
        )

    def _on_listed(self, rows):
        self._busy(False)
        self._rows = sorted(rows, key=lambda r: r['created_at'], reverse=True)
        self._list.DeleteAllItems()
        for r in self._rows:
            idx = self._list.InsertItem(self._list.GetItemCount(),
                                        str(r['created_at']))
            self._list.SetItem(idx, 1, os.path.basename(str(r['file'])))
            self._list.SetItem(idx, 2, str(r['platform']))

    def _selected_pk(self):
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return None
        return int(self._rows[idx]['pk'])

    def _on_download(self, _evt):
        pk = self._selected_pk()
        if pk is None:
            return
        self._busy(True)
        _run_in_thread(
            lambda: _download_and_import(self._client, self._presenter, pk),
            on_success=self._on_imported,
            on_error=self._on_err,
        )

    def _on_imported(self, _result):
        self._busy(False)
        wx.MessageBox(u'นำเข้าข้อมูลสำเร็จ', MSGBOX_TITLE,
                      wx.OK | wx.ICON_INFORMATION, self)

    def _on_delete(self, _evt):
        pk = self._selected_pk()
        if pk is None:
            return
        if wx.MessageBox(u'ลบข้อมูลสำรองนี้ถาวรหรือไม่?', u'ยืนยัน',
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.delete_backup(pk),
            on_success=lambda _r: self._refresh(),
            on_error=self._on_err,
        )

    def _on_err(self, err):
        self._busy(False)
        _show_error(self, err)

    def _busy(self, on):
        for b in (self._btnDownload, self._btnDelete, self._btnClose):
            b.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()


def _download_and_import(client, presenter, pk):
    data = client.download(pk)
    fd, tmp = tempfile.mkstemp(suffix='.etz')
    os.close(fd)
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        presenter.ImportPCData(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _build_and_upload(client, presenter, username):
    from search.presenter import BuildBackupZip
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    filename = 'backup-%s-%s.etz' % (timestamp, username)
    fd, tmp = tempfile.mkstemp(suffix='.etz')
    os.close(fd)
    try:
        BuildBackupZip(tmp)
        client.upload(tmp, filename)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return datetime.now().isoformat(timespec='seconds')


def _download_latest(client, presenter):
    rows = client.list_backups(platform='pc')
    if not rows:
        raise AccountError(404, u'ไม่พบข้อมูลสำรองของ PC บนเซิร์ฟเวอร์')
    rows.sort(key=lambda r: r['created_at'], reverse=True)
    _download_and_import(client, presenter, int(rows[0]['pk']))


class AccountDialog(wx.Dialog):

    def __init__(self, parent, client, tokenstore, presenter):
        super(AccountDialog, self).__init__(parent, title=u'บัญชีผู้ใช้',
                                            size=(380, 280))
        self._client = client
        self._store = tokenstore
        self._presenter = presenter

        self._panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._panel.SetSizer(self._sizer)

        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []

        self._render()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, evt):
        # Veto window-manager close while a worker thread is in-flight.
        if any(not b.IsEnabled() for b in self._actionButtons):
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _render(self):
        self._sizer.Clear(delete_windows=True)
        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []
        if self._store.is_logged_in():
            self._render_logged_in()
        else:
            self._render_logged_out()
        self._panel.Layout()
        self.Layout()

    def _render_logged_out(self):
        grid = wx.FlexGridSizer(rows=3, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self._panel, label=u'เข้าสู่ระบบ: -'))
        grid.Add(wx.StaticText(self._panel, label=''))
        self._username = wx.TextCtrl(self._panel)
        self._password = wx.TextCtrl(self._panel, style=wx.TE_PASSWORD)
        grid.Add(wx.StaticText(self._panel, label=u'ชื่อผู้ใช้'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._username, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self._panel, label=u'รหัสผ่าน'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._password, 1, wx.EXPAND)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnLogin = wx.Button(self._panel, label=u'เข้าสู่ระบบ')
        btnSignup = wx.Button(self._panel, label=u'สมัครสมาชิก...')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label=u'ปิด')
        btnLogin.Bind(wx.EVT_BUTTON, self._on_login)
        btnSignup.Bind(wx.EVT_BUTTON, self._on_signup)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        btnRow.Add(btnLogin, 0, wx.RIGHT, 6)
        btnRow.Add(btnSignup, 0)
        btnRow.AddStretchSpacer()
        btnRow.Add(btnClose, 0)

        self._actionButtons = [btnLogin, btnSignup, btnClose]

        self._sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)

    def _render_logged_in(self):
        data = self._store.get() or {}
        info = wx.BoxSizer(wx.VERTICAL)
        info.Add(wx.StaticText(self._panel,
            label=u'เข้าสู่ระบบ: %s' % data.get('username', '')), 0, wx.BOTTOM, 4)
        last = data.get('last_upload', '-')
        info.Add(wx.StaticText(self._panel, label=u'อัปโหลดล่าสุด: %s' % last),
                 0, wx.BOTTOM, 4)

        btnUpload = wx.Button(self._panel, label=u'อัปโหลดขึ้นคลาวด์')
        btnDownload = wx.Button(self._panel, label=u'ดาวน์โหลดล่าสุด')
        btnManage = wx.Button(self._panel, label=u'จัดการข้อมูลสำรอง...')
        btnLogout = wx.Button(self._panel, label=u'ออกจากระบบ')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label=u'ปิด')
        btnUpload.Bind(wx.EVT_BUTTON, self._on_upload)
        btnDownload.Bind(wx.EVT_BUTTON, self._on_download_latest)
        btnManage.Bind(wx.EVT_BUTTON, self._on_manage)
        btnLogout.Bind(wx.EVT_BUTTON, self._on_logout)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))

        actions = wx.BoxSizer(wx.VERTICAL)
        actions.Add(btnUpload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnDownload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnManage, 0, wx.EXPAND)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        bottom.Add(btnLogout, 0)
        bottom.AddStretchSpacer()
        bottom.Add(btnClose, 0)

        self._actionButtons = [btnUpload, btnDownload, btnManage, btnLogout, btnClose]

        self._sizer.Add(info, 0, wx.ALL, 10)
        self._sizer.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(bottom, 0, wx.EXPAND | wx.ALL, 10)

    def _on_login(self, _evt):
        u = self._username.GetValue().strip()
        p = self._password.GetValue()
        if not (u and p):
            wx.MessageBox(u'ต้องระบุชื่อผู้ใช้และรหัสผ่าน',
                          u'เข้าสู่ระบบ', wx.OK | wx.ICON_WARNING, self)
            return
        self._busy(True)
        _run_in_thread(
            lambda: self._client.login(u, p),
            on_success=lambda _r: (self._busy(False), self._render()),
            on_error=self._on_err,
        )

    def _on_signup(self, _evt):
        dlg = SignUpDialog(self, self._client)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_upload(self, _evt):
        data = self._store.get() or {}
        username = data.get('username', 'user')
        self._busy(True)
        _run_in_thread(
            lambda: _build_and_upload(self._client, self._presenter, username),
            on_success=self._on_uploaded,
            on_error=self._on_err,
        )

    def _on_uploaded(self, iso_timestamp):
        self._store.set_last_upload(iso_timestamp)
        self._busy(False)
        wx.MessageBox(u'อัปโหลดสำเร็จ', MSGBOX_TITLE,
                      wx.OK | wx.ICON_INFORMATION, self)
        self._render()

    def _on_download_latest(self, _evt):
        self._busy(True)
        _run_in_thread(
            lambda: _download_latest(self._client, self._presenter),
            on_success=lambda _r: (self._busy(False),
                wx.MessageBox(u'นำเข้าข้อมูลสำเร็จ', MSGBOX_TITLE,
                              wx.OK | wx.ICON_INFORMATION, self)),
            on_error=self._on_err,
        )

    def _on_manage(self, _evt):
        dlg = BackupListDialog(self, self._client, self._presenter)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_logout(self, _evt):
        self._busy(True)
        _run_in_thread(
            lambda: self._client.logout(),
            on_success=lambda _r: (self._store.clear(), self._busy(False),
                                   self._render()),
            on_error=lambda e: (self._store.clear(), self._busy(False),
                                self._render()),
        )

    def _on_err(self, err):
        if err.status == 401:
            self._store.clear()
        self._busy(False)
        _show_error(self, err)
        if err.status == 401:
            self._render()

    def _busy(self, on):
        for b in self._actionButtons:
            b.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()

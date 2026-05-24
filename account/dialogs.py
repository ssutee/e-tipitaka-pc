#-*- coding:utf-8 -*-

import os
import tempfile
import threading
from datetime import datetime

import wx

from account.client import AccountError


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
        msg = 'Session expired, please log in again.'
    elif err.status == 404:
        msg = 'Backup not found.'
    elif err.status == 0:
        msg = 'Cannot reach server; check your internet connection.\n\n%s' % err.message
    else:
        msg = err.message or ('HTTP %d' % err.status)
    wx.MessageBox(msg, 'E-Tipitaka — Account', wx.OK | wx.ICON_ERROR, parent)


class SignUpDialog(wx.Dialog):

    def __init__(self, parent, client):
        super(SignUpDialog, self).__init__(parent, title='Sign up',
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

        for label, ctrl in [('Email', self._email),
                            ('Username', self._username),
                            ('Password', self._password),
                            ('Confirm', self._confirm)]:
            grid.Add(wx.StaticText(panel, label=label),
                     flag=wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        self._btnOk = wx.Button(panel, label='Sign up')
        self._btnCancel = wx.Button(panel, wx.ID_CANCEL, label='Cancel')
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
            wx.MessageBox('Email, username and password are required.',
                          'Sign up', wx.OK | wx.ICON_WARNING, self)
            return
        if pw != cf:
            wx.MessageBox('Passwords do not match.', 'Sign up',
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
            wx.MessageBox('Verification email sent to %s.' % email,
                          'Sign up', wx.OK | wx.ICON_INFORMATION, self)
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
        super(BackupListDialog, self).__init__(parent, title='Manage backups',
                                               size=(560, 360))
        self._client = client
        self._presenter = presenter

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._list.InsertColumn(0, 'Date', width=170)
        self._list.InsertColumn(1, 'Filename', width=240)
        self._list.InsertColumn(2, 'Platform', width=80)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_download)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        self._btnDownload = wx.Button(panel, label='Download')
        self._btnDelete = wx.Button(panel, label='Delete')
        self._btnClose = wx.Button(panel, wx.ID_CLOSE, label='Close')
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
        wx.MessageBox('Import complete.', 'E-Tipitaka — Account',
                      wx.OK | wx.ICON_INFORMATION, self)

    def _on_delete(self, _evt):
        pk = self._selected_pk()
        if pk is None:
            return
        if wx.MessageBox('Delete this backup permanently?', 'Confirm',
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
        raise AccountError(404, 'No PC backups found on server.')
    rows.sort(key=lambda r: r['created_at'], reverse=True)
    _download_and_import(client, presenter, int(rows[0]['pk']))


class AccountDialog(wx.Dialog):

    def __init__(self, parent, client, tokenstore, presenter):
        super(AccountDialog, self).__init__(parent, title='Account',
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
        grid.Add(wx.StaticText(self._panel, label='Signed in: -'))
        grid.Add(wx.StaticText(self._panel, label=''))
        self._username = wx.TextCtrl(self._panel)
        self._password = wx.TextCtrl(self._panel, style=wx.TE_PASSWORD)
        grid.Add(wx.StaticText(self._panel, label='Username'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._username, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self._panel, label='Password'),
                 flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._password, 1, wx.EXPAND)

        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnLogin = wx.Button(self._panel, label='Login')
        btnSignup = wx.Button(self._panel, label='Sign up...')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label='Close')
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
            label='Signed in: %s' % data.get('username', '')), 0, wx.BOTTOM, 4)
        last = data.get('last_upload', '-')
        info.Add(wx.StaticText(self._panel, label='Last upload: %s' % last),
                 0, wx.BOTTOM, 4)

        btnUpload = wx.Button(self._panel, label='Upload to Cloud')
        btnDownload = wx.Button(self._panel, label='Download latest')
        btnManage = wx.Button(self._panel, label='Manage backups...')
        btnLogout = wx.Button(self._panel, label='Logout')
        btnClose = wx.Button(self._panel, wx.ID_CLOSE, label='Close')
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
            wx.MessageBox('Username and password are required.',
                          'Login', wx.OK | wx.ICON_WARNING, self)
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
        wx.MessageBox('Upload complete.', 'E-Tipitaka — Account',
                      wx.OK | wx.ICON_INFORMATION, self)
        self._render()

    def _on_download_latest(self, _evt):
        self._busy(True)
        _run_in_thread(
            lambda: _download_latest(self._client, self._presenter),
            on_success=lambda _r: (self._busy(False),
                wx.MessageBox('Import complete.', 'E-Tipitaka — Account',
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

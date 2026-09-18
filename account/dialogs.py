#-*- coding:utf-8 -*-

import os
import tempfile
import threading
import webbrowser
import zipfile
from datetime import datetime

import wx

import constants
from account.client import AccountError
from account.pairing import PairingSession, DENIED, EXPIRED


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
            # Distinguish network errors (status=0 → "cannot reach server"
            # message) from local/unexpected errors (status=-1 → show
            # message verbatim via the else-branch of _show_error).
            try:
                import requests.exceptions as _re
                is_network = isinstance(e, _re.RequestException)
            except Exception:
                is_network = False
            status = 0 if is_network else -1
            wx.CallAfter(on_error, AccountError(status, str(e)))
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

    # (platform_key, tab_label) — tab order = display order.
    PLATFORMS = [('pc', 'PC'), ('android', 'Android'), ('ios', 'iOS')]

    def __init__(self, parent, client, presenter):
        super(BackupListDialog, self).__init__(parent, title=u'จัดการข้อมูลสำรอง',
                                               size=(560, 360))
        self._client = client
        self._presenter = presenter

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._notebook = wx.Notebook(panel)
        self._lists = {}    # platform -> ListCtrl
        self._rows = {}     # platform -> list of dicts
        for plat, label in self.PLATFORMS:
            page = wx.Panel(self._notebook)
            psizer = wx.BoxSizer(wx.VERTICAL)
            lc = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            lc.InsertColumn(0, u'วันที่', width=180)
            lc.InsertColumn(1, u'ชื่อไฟล์', width=320)
            lc.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_download)
            psizer.Add(lc, 1, wx.EXPAND | wx.ALL, 4)
            page.SetSizer(psizer)
            self._notebook.AddPage(page, label)
            self._lists[plat] = lc
            self._rows[plat] = []
        self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)

        self._gauge = wx.Gauge(panel)
        self._gauge.Hide()

        self._btnRow = wx.BoxSizer(wx.HORIZONTAL)
        self._btnDownload = wx.Button(panel, label=u'ดาวน์โหลด')
        self._btnDelete = wx.Button(panel, label=u'ลบ')
        self._btnClose = wx.Button(panel, wx.ID_CLOSE, label=u'ปิด')
        self._btnDownload.Bind(wx.EVT_BUTTON, self._on_download)
        self._btnDelete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        self._btnRow.Add(self._btnDownload, 0, wx.RIGHT, 6)
        self._btnRow.Add(self._btnDelete, 0, wx.RIGHT, 6)
        self._btnRow.AddStretchSpacer()
        self._btnRow.Add(self._btnClose, 0)

        sizer.Add(self._notebook, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self._btnRow, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._refresh()

    def _current_platform(self):
        return self.PLATFORMS[self._notebook.GetSelection()][0]

    def _on_page_changed(self, evt):
        evt.Skip()

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
        for plat in self._rows:
            self._rows[plat] = []
            self._lists[plat].DeleteAllItems()
        for r in rows:
            plat = str(r.get('platform', '')).lower()
            if plat not in self._rows:
                continue  # skip unknown platform values silently
            self._rows[plat].append(r)
        for plat, lc in self._lists.items():
            self._rows[plat].sort(key=lambda r: r['created_at'], reverse=True)
            for r in self._rows[plat]:
                idx = lc.InsertItem(lc.GetItemCount(), str(r['created_at']))
                lc.SetItem(idx, 1, os.path.basename(str(r['file'])))

    def _selected_pk(self):
        plat = self._current_platform()
        lc = self._lists[plat]
        idx = lc.GetFirstSelected()
        if idx < 0:
            return None
        return int(self._rows[plat][idx]['pk'])

    def _on_download(self, _evt):
        plat = self._current_platform()
        pk = self._selected_pk()
        if pk is None:
            return
        self._busy(True)
        _run_in_thread(
            lambda: _download_and_import(self._client, self._presenter, pk, plat),
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


_PLATFORM_DISPATCH = {
    # platform -> (file_suffix, presenter_method_name, error_message)
    'pc':      ('.etz',  'ImportPCData',      u'ไฟล์ที่ดาวน์โหลดไม่ใช่ไฟล์สำรองของ PC (ต้องเป็นไฟล์ .etz)'),
    'ios':     ('.json', 'ImportIOSData',     u'ไฟล์ที่ดาวน์โหลดไม่ใช่ไฟล์สำรองของ iOS'),
    'android': ('.js',   'ImportAndroidData', u'ไฟล์ที่ดาวน์โหลดไม่ใช่ไฟล์สำรองของ Android'),
}


def _download_and_import(client, presenter, pk, platform='pc'):
    spec = _PLATFORM_DISPATCH.get(platform)
    if spec is None:
        raise AccountError(415, u'แพลตฟอร์มไม่รองรับ: %s' % platform)
    suffix, method_name, fmt_err = spec
    importer = getattr(presenter, method_name)

    data = client.download(pk)
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        try:
            importer(tmp)
        except zipfile.BadZipFile:
            raise AccountError(422, fmt_err)
        except (ValueError, KeyError):
            # JSON parse error or missing expected field — content is not
            # the format the importer expected.
            raise AccountError(422, fmt_err)
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
                                            size=(420, 380))
        self._client = client
        self._store = tokenstore
        self._presenter = presenter

        self._pairing = None        # the PairingSession in flight, if any
        self._pairing_url = None
        # A single Gauge.Pulse() animates continuously on macOS and Windows
        # but moves one step on GTK, and a pairing can last ten minutes.
        self._pulse = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_pulse, self._pulse)

        self._panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._panel.SetSizer(self._sizer)

        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []

        self._render()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, evt):
        if self._pairing is not None:
            # A pairing can run for ten minutes, so closing the window
            # cancels it instead of being vetoed. cancel() guarantees nothing
            # fires into this dialog afterwards -- the danger the veto below
            # exists to prevent for the short requests, which cannot be
            # cancelled.
            self._cancel_pairing()
        elif any(not b.IsEnabled() for b in self._actionButtons):
            # Veto window-manager close while a worker thread is in-flight.
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _reset(self):
        self._pulse.Stop()
        self._sizer.Clear(delete_windows=True)
        self._gauge = wx.Gauge(self._panel)
        self._gauge.Hide()
        self._actionButtons = []

    def _relayout(self):
        # Grow, never shrink: 420x380 is sized for macOS, and GTK's taller
        # Thai lines and 34px buttons need more on the signed-out screen.
        need, have = self._panel.GetBestSize(), self.GetClientSize()
        if need.width > have.width or need.height > have.height:
            self.SetClientSize((max(need.width, have.width),
                                max(need.height, have.height)))
        self._panel.Layout()
        self.Layout()

    def _render(self):
        self._reset()
        if self._store.is_logged_in():
            self._render_logged_in()
        else:
            self._render_logged_out()
        self._relayout()

    def _render_logged_out(self):
        status = wx.StaticText(self._panel, label=u'เข้าสู่ระบบ: -')

        # The primary action. The label must stay exactly this: the
        # confirmation page in the browser asks whether the user just pressed
        # "เข้าสู่ระบบด้วยพาสคีย์" on their computer, quoting it by name.
        btnPasskey = wx.Button(self._panel, label=u'เข้าสู่ระบบด้วยพาสคีย์')
        btnPasskey.Bind(wx.EVT_BUTTON, self._on_passkey_login)

        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=6, hgap=6)
        grid.AddGrowableCol(1, 1)
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

        btnPasskeySignup = wx.Button(self._panel,
                                     label=u'สมัครสมาชิกด้วยพาสคีย์...')
        btnRecover = wx.Button(self._panel,
                               label=u'ลืมรหัสผ่าน / พาสคีย์หาย...')
        btnPasskeySignup.Bind(wx.EVT_BUTTON, self._on_passkey_signup)
        btnRecover.Bind(wx.EVT_BUTTON, self._on_recover)
        # Stacked, not side by side: two Thai labels this long do not fit
        # across 420px on every platform's default font.
        linkCol = wx.BoxSizer(wx.VERTICAL)
        linkCol.Add(btnPasskeySignup, 0, wx.EXPAND | wx.BOTTOM, 4)
        linkCol.Add(btnRecover, 0, wx.EXPAND)

        self._actionButtons = [btnPasskey, btnLogin, btnSignup, btnClose,
                               btnPasskeySignup, btnRecover]

        self._sizer.Add(status, 0, wx.ALL, 10)
        self._sizer.Add(btnPasskey, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(wx.StaticText(self._panel,
                        label=u'หรือใช้ชื่อผู้ใช้และรหัสผ่าน'),
                        0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(linkCol, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

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
        btnPasskeys = wx.Button(self._panel, label=u'จัดการพาสคีย์...')
        btnPasskeys.Bind(wx.EVT_BUTTON, self._on_manage_passkeys)
        btnLogout.Bind(wx.EVT_BUTTON, self._on_logout)
        btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))

        actions = wx.BoxSizer(wx.VERTICAL)
        actions.Add(btnUpload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnDownload, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnManage, 0, wx.EXPAND | wx.BOTTOM, 4)
        actions.Add(btnPasskeys, 0, wx.EXPAND)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        bottom.Add(btnLogout, 0)
        bottom.AddStretchSpacer()
        bottom.Add(btnClose, 0)

        self._actionButtons = [btnUpload, btnDownload, btnManage, btnPasskeys,
                               btnLogout, btnClose]

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

    # --- passkey sign-in ---------------------------------------------------

    def _on_passkey_login(self, _evt):
        self._busy(True)
        self._pairing = PairingSession(
            self._client, self._store,
            on_code=self._show_pairing,
            on_done=self._on_pairing_done,
            on_error=self._on_pairing_error,
            dispatch=wx.CallAfter)
        self._pairing.start()

    def _show_pairing(self, user_code, url):
        self._pairing_url = url
        self._reset()
        self._render_pairing(user_code)
        self._relayout()
        self._pulse.Start(100)
        # The app opens the page itself, so the honest flow never involves
        # following a pairing link from anywhere else -- with the code in the
        # URL, a link from elsewhere is exactly what a phisher would send.
        # Rendered first, so the code is on screen before the browser takes
        # focus.
        self._open_browser(url)

    def _render_pairing(self, user_code):
        col = wx.BoxSizer(wx.VERTICAL)
        # Name the app beside the code: the browser page cannot say which
        # computer is asking, so this screen is the only place that can.
        col.Add(wx.StaticText(self._panel,
                label=u'E-Tipitaka บนคอมพิวเตอร์เครื่องนี้แสดงรหัส:'),
                0, wx.BOTTOM, 6)
        code = wx.StaticText(self._panel, label=user_code)
        code.SetFont(wx.Font(24, wx.FONTFAMILY_TELETYPE,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        col.Add(code, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 8)
        # A no-break space keeps the quoted button name on one line.
        hint = wx.StaticText(self._panel, label=(
            u'ลงชื่อเข้าใช้ในเบราว์เซอร์ที่เปิดขึ้น แล้วตรวจว่าหน้าเว็บแสดงรหัส'
            u'เดียวกันนี้ ถ้าไม่ตรงกัน อย่ากด "ใช่\u00a0อนุญาต"'))
        hint.Wrap(380)
        col.Add(hint, 0, wx.BOTTOM, 10)
        self._gauge.Show()
        col.Add(self._gauge, 0, wx.EXPAND | wx.BOTTOM, 4)
        col.Add(wx.StaticText(self._panel,
                label=u'กำลังรอการยืนยันในเบราว์เซอร์...'), 0)

        btnReopen = wx.Button(self._panel, label=u'เปิดเบราว์เซอร์อีกครั้ง')
        # wx.ID_CANCEL, so Esc cancels too. The handler below does not Skip(),
        # so the dialog's default Esc handling never ends the modal.
        btnCancel = wx.Button(self._panel, wx.ID_CANCEL, label=u'ยกเลิก')
        btnReopen.Bind(wx.EVT_BUTTON,
                       lambda _e: self._open_browser(self._pairing_url))
        btnCancel.Bind(wx.EVT_BUTTON, self._on_cancel_pairing)
        btnRow = wx.BoxSizer(wx.HORIZONTAL)
        btnRow.Add(btnReopen, 0)
        btnRow.AddStretchSpacer()
        btnRow.Add(btnCancel, 0)

        self._actionButtons = [btnReopen, btnCancel]

        self._sizer.Add(col, 1, wx.EXPAND | wx.ALL, 10)
        self._sizer.Add(btnRow, 0, wx.EXPAND | wx.ALL, 10)

    def _on_pulse(self, _evt):
        self._gauge.Pulse()

    def _on_cancel_pairing(self, _evt):
        self._cancel_pairing()
        self._render()

    def _cancel_pairing(self):
        if self._pairing is not None:
            self._pairing.cancel()
            self._pairing = None
        self._pulse.Stop()

    def _on_pairing_done(self, _username):
        self._pairing = None
        self._render()          # the store now holds the token
        # The user is still in the browser: bounce the Dock icon / flash the
        # taskbar so they know to come back.
        self.RequestUserAttention()

    def _on_pairing_error(self, reason, err):
        self._pairing = None
        self._render()
        if reason == DENIED:
            wx.MessageBox(u'คำขอเข้าสู่ระบบถูกปฏิเสธในเบราว์เซอร์',
                          MSGBOX_TITLE, wx.OK | wx.ICON_INFORMATION, self)
        elif reason == EXPIRED:
            wx.MessageBox(u'คำขอเข้าสู่ระบบหมดอายุแล้ว กรุณาลองใหม่',
                          MSGBOX_TITLE, wx.OK | wx.ICON_WARNING, self)
        elif err.status == 0:
            _show_error(self, err)      # "cannot reach the server"
        else:
            # Not _show_error for the rest: its 401 and 404 wording is about
            # an existing session and backups. Say what failed, then why --
            # the server's Thai, or a local error such as a full disk. A 5xx
            # body is usually a proxy's HTML page, so name the status instead.
            detail = err.message
            if err.status >= 500 or not detail:
                detail = u'HTTP %d' % err.status
            wx.MessageBox(u'เข้าสู่ระบบด้วยพาสคีย์ไม่สำเร็จ\n\n%s' % detail,
                          MSGBOX_TITLE, wx.OK | wx.ICON_ERROR, self)

    def _open_browser(self, url):
        if not webbrowser.open_new(url):
            wx.MessageBox(
                u'เปิดเบราว์เซอร์ไม่ได้ กรุณาคัดลอกลิงก์นี้ไปเปิดเอง:\n\n%s' % url,
                MSGBOX_TITLE, wx.OK | wx.ICON_WARNING, self)

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

    def _on_passkey_signup(self, _evt):
        # No token comes back: a passkey sign-up leaves the account inactive
        # until the emailed link is opened. The user then signs in here with
        # เข้าสู่ระบบด้วยพาสคีย์.
        self._open_browser(constants.ACCOUNT_SIGNUP_URL)

    def _on_recover(self, _evt):
        self._open_browser(constants.ACCOUNT_RECOVER_URL)

    def _on_manage_passkeys(self, _evt):
        # The page signs in on its own; the app does not carry its token
        # into the browser.
        self._open_browser(constants.ACCOUNT_PASSKEYS_URL)

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
        # The gauge lives on the panel: laying out only the dialog leaves it
        # a sliver at the panel's origin, over the status line.
        self._relayout()

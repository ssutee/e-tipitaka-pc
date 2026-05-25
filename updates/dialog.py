#-*- coding:utf-8 -*-

"""wx UI for the online db-patch updater. Two surfaces:

- `check_in_background(parent, on_done)` — non-UI worker that fetches the
  index and reports a list of pending patches via wx.CallAfter. Used by
  the startup auto-check.
- `UpdatesDialog` — modal that asks the user to confirm + shows progress.
  Used both for the manual menu entry and as the prompt after the auto
  check finds pending patches.
"""

import os
import threading

import wx

import constants
from updates import patcher


MSGBOX_TITLE = u'E-Tipitaka — อัปเดตฐานข้อมูล'


def check_in_background(on_done, downloader=None):
    """Run the (network-bound) index fetch on a worker thread. Calls
    `on_done(pending_list)` on the wx main thread when finished. Network
    errors are swallowed silently (per Q5) — `on_done([])` fires."""
    def _target():
        try:
            pending = patcher.check_for_updates(
                constants.PATCH_INDEX_URL, downloader=downloader)
        except Exception:
            pending = []
        wx.CallAfter(on_done, pending)
    threading.Thread(target=_target, daemon=True).start()


class UpdatesDialog(wx.Dialog):
    """Confirm + progress dialog. Pass `pending` when you already know
    what's available (post-auto-check); pass nothing to trigger a fresh
    fetch on open (manual menu)."""

    def __init__(self, parent, pending):
        super(UpdatesDialog, self).__init__(parent, title=u'อัปเดตฐานข้อมูล',
                                            size=(420, 260))
        if not pending:
            raise ValueError('UpdatesDialog requires non-empty pending; '
                             'the menu handler is responsible for the '
                             '"up to date" alert and never opens the '
                             'dialog on empty results.')
        self._pending = pending

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._label = wx.StaticText(panel, label=u'กำลังตรวจสอบการอัปเดต...')
        self._gauge = wx.Gauge(panel)
        self._list = wx.ListCtrl(panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self._list.InsertColumn(0, u'ฐานข้อมูล', width=150)
        self._list.InsertColumn(1, u'จาก', width=70)
        self._list.InsertColumn(2, u'ถึง', width=70)
        self._list.InsertColumn(3, u'สถานะ', width=100)

        self._btnApply = wx.Button(panel, label=u'ติดตั้งอัปเดต')
        self._btnClose = wx.Button(panel, wx.ID_CLOSE, label=u'ปิด')
        self._btnApply.Bind(wx.EVT_BUTTON, self._on_apply)
        self._btnClose.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_OK))
        self._btnApply.Disable()

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.Add(self._btnApply, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._btnClose, 0)

        sizer.Add(self._label, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._busy = False
        self._on_pending(pending)

    def _on_close(self, evt):
        if self._busy:
            evt.Veto()
            return
        self.EndModal(wx.ID_OK)

    def _set_busy(self, on):
        self._busy = on
        self._btnApply.Enable(not on)
        self._btnClose.Enable(not on)
        if on:
            self._gauge.Show()
            self._gauge.Pulse()
        else:
            self._gauge.Hide()
        self.Layout()

    def _on_pending(self, pending):
        self._set_busy(False)
        self._pending = pending
        self._list.DeleteAllItems()
        self._label.SetLabel(
            u'พบการอัปเดต %d รายการ ต้องการติดตั้งหรือไม่?' % len(pending))
        for key, patch, _ship in pending:
            first_from = patch.chain[0][0]
            last_to = patch.chain[-1][1]
            idx = self._list.InsertItem(self._list.GetItemCount(), key)
            self._list.SetItem(idx, 1, str(first_from))
            self._list.SetItem(idx, 2, str(last_to))
            self._list.SetItem(idx, 3, u'รอติดตั้ง')
        self._btnApply.Enable()
        self.Layout()

    def _on_apply(self, _evt):
        if not self._pending:
            return
        self._set_busy(True)
        self._label.SetLabel(u'กำลังติดตั้งอัปเดต...')

        def _target():
            results = patcher.apply_pending(self._pending)
            wx.CallAfter(self._on_applied, results)
        threading.Thread(target=_target, daemon=True).start()

    def _on_applied(self, results):
        self._set_busy(False)
        for i, (key, _patch, _ship) in enumerate(self._pending):
            status = results.get(key, '?')
            label = u'สำเร็จ' if status == 'ok' else (u'ผิดพลาด: %s' % status)
            self._list.SetItem(i, 3, label)
        ok_count = sum(1 for v in results.values() if v == 'ok')
        fail_count = len(results) - ok_count
        if fail_count == 0:
            self._label.SetLabel(u'ติดตั้งอัปเดตสำเร็จ %d รายการ' % ok_count)
        else:
            self._label.SetLabel(
                u'สำเร็จ %d ผิดพลาด %d' % (ok_count, fail_count))
        self._btnApply.Disable()
        self.Layout()

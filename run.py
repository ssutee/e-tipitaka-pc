#!/usr/bin/env python3

import os, sys, traceback, datetime, glob

# Force macOS light appearance: wxWidgets 3.2 has no SetAppearance API, and the
# UI is unreadable under the system dark theme. Re-exec once with the argument
# so NSUserDefaults' argument domain forces a light system appearance. A frozen
# bundle gets this from its Info.plist instead, so only do it when run from source.
if sys.platform == 'darwin' and not getattr(sys, 'frozen', False) \
        and '-NSRequiresAquaSystemAppearance' not in sys.argv:
    os.execv(sys.executable,
             [sys.executable, os.path.abspath(__file__)] + sys.argv[1:]
             + ['-NSRequiresAquaSystemAppearance', 'YES'])

import constants

if not os.path.exists(constants.DATA_PATH):
    os.makedirs(constants.DATA_PATH)

if not os.path.exists(constants.LOG_PATH):
    os.makedirs(constants.LOG_PATH)

import utils
import settings

utils.UpdateDatabases()

import search.view
import search.interactor
import search.presenter
import search.model

import read.model
import read.interactor
import read.view
import read.presenter

import wx

import wx.lib.agw.aui as aui  # pure-Python AUI; C++ wx.aui MDI frames segfault on macOS

# Work around an AGW AUI bug: AuiDefaultTabArt.GetBestTabCtrlSize uses a local
# 'bmp' that is only bound when no standard bitmap size is enforced, so it
# raises UnboundLocalError when one is (e.g. on Windows).
import wx.lib.agw.aui.tabart as _tabart
def _GetBestTabCtrlSize(self, wnd, pages, required_bmp_size):
    dc = wx.ClientDC(wnd)
    dc.SetFont(self._measuring_font)
    measure_bmp = wx.NullBitmap
    if required_bmp_size.IsFullySpecified():
        measure_bmp = wx.Bitmap(required_bmp_size.x, required_bmp_size.y)
    measure_bmp_isok = measure_bmp.IsOk()
    max_y = 0
    for page in pages:
        bmp = measure_bmp if measure_bmp_isok else page.bitmap
        s, x_ext = self.GetTabSize(dc, wnd, page.caption, bmp, True,
                                   _tabart.AUI_BUTTON_STATE_HIDDEN, None)
        max_y = max(max_y, s[1])
        if page.control:
            max_y = max(max_y, page.control.GetSize()[1] + 4)
    return max_y + 2
_tabart.AuiDefaultTabArt.GetBestTabCtrlSize = _GetBestTabCtrlSize

import i18n
_ = i18n.language.ugettext

class ParentFrame(aui.AuiMDIParentFrame):

    @property
    def ProgressBar(self):
        return self._progressBar

    @property
    def StatusBar(self):
        return self._statusBar

    @property
    def Presenter(self):
        return self._presenter

    @Presenter.setter
    def Presenter(self, value):
        self._presenter = value

    def __init__(self, parent):
        appname = '%s (%s)' % (_('AppName'), 'E-Tipitaka' + ' v' + settings.VERSION)

        rect = utils.LoadSearchWindowPosition()
        pos = 0,0
        if rect is not None:
            pos = rect[0], rect[1]
        size = min(1024, wx.DisplaySize()[0]), min(748, wx.DisplaySize()[1])
        if rect is not None:
            size = rect[2], rect[3]

        aui.AuiMDIParentFrame.__init__(self, parent, wx.ID_ANY, title=appname,
            pos=pos, size=size, style=wx.DEFAULT_FRAME_STYLE)

        icon = wx.IconBundle()
        icon.AddIcon(constants.ICON_IMAGE, wx.BITMAP_TYPE_ANY)

        self.SetIcons(icon)

        self.Bind(wx.EVT_CLOSE, self.OnFrameClose)
        self._CreateStatusBar()
        self._CreateMenuBar()

        view = search.view.View(self)
        interactor = search.interactor.Interactor()
        model = search.model.ThaiRoyalSearchModel(None)

        self._presenter = search.presenter.Presenter(model, view, interactor)
        self._presenter.Delegate = self

        self._presenters = {}

        if rect is None:
            self.CenterOnScreen()


    def _CreateStatusBar(self):
        self._statusBar = self.CreateStatusBar()
        self._statusBar.SetFieldsCount(4)
        self._statusBar.SetStatusWidths([-1,170,170,100])

        self._progressBar = wx.Gauge(self._statusBar, -1, 100, size=(100,-1))
        self._progressBar.SetRect(self._statusBar.GetFieldRect(3))

    def _CreateMenuBar(self):
        bar = wx.MenuBar()
        helpMenu = wx.Menu()
        checkItem = helpMenu.Append(wx.ID_ANY, u'ตรวจสอบอัปเดตฐานข้อมูล')
        self.Bind(wx.EVT_MENU, lambda _e: self.ShowUpdatesDialog(), checkItem)
        bar.Append(helpMenu, u'E-Tipitaka')
        self.SetMenuBar(bar)

    def ShowUpdatesDialog(self, pending=None):
        # Lazy import: wx.Dialog subclass + requests pulled only on demand.
        from updates.dialog import UpdatesDialog
        dlg = UpdatesDialog(self, pending=pending)
        dlg.ShowModal()
        dlg.Destroy()

    def StartAutoUpdateCheck(self):
        """Kick off a background fetch a few seconds after the UI settles.
        If anything pending, surface the confirm dialog. Silent otherwise
        (per Q5 — network failures never bother the user)."""
        from updates.dialog import check_in_background

        def _on_pending(pending):
            if not pending or not self:
                return
            self.ShowUpdatesDialog(pending=pending)
        wx.CallLater(3000, check_in_background, _on_pending)

    def PositionProgressBar(self):
        if self: self._progressBar.SetRect(self._statusBar.GetFieldRect(3))

    def PostInit(self):
        self._statusBar.Bind(wx.EVT_SIZE, lambda event: wx.CallAfter(self.PositionProgressBar))

    def ProcessEvent(self, event):
        # AGW's AuiMDIParentFrame.ProcessEvent routes command events to the
        # active MDI child, but its _pLastEvt re-entrancy guard silently drops
        # non-command events (size, close, ...) because GetEventHandler() is
        # self -- leaving the child window unsized and the frame unclosable.
        # Route command events through AGW; handle the rest with base wx.Frame.
        if event.IsCommandEvent():
            return aui.AuiMDIParentFrame.ProcessEvent(self, event)
        return wx.Frame.ProcessEvent(self, event)

    def OnFrameClose(self, event):
        try:
            self._presenter._canBeClosed = True
            utils.SaveSearchWindowPosition(self)
            if self._presenter: self._presenter.SaveSearches()
            for code in self._presenters:
                self._presenter.SaveHistory(code)
            for child in self.GetClientWindow().GetChildren():
                if isinstance(child, aui.AuiMDIChildFrame):
                    try:
                        child.Close()
                    except Exception:
                        pass
        except Exception:
            traceback.print_exc()
        self.Destroy()

    def ReadAndCompare(self, code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords, code2, volume2, page2, keywords2):
        presenter = self.Read(code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords)
        index = presenter.View.AddReadPanel(code2)
        presenter.OpenAnotherBook(code2, index, volume2, page2, keywords2)


    def Read(self, code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords=None):
        self._presenter.SetFocus()

        presenter = None if self._presenters.get(code) is None else self._presenters.get(code)[0]

        if not presenter or shouldOpenNewWindow:
            model = read.model.Model(code)
            view = read.view.View(self, '%s'%(utils.ShortName(code)), code)
            interactor = read.interactor.Interactor()
            presenter = read.presenter.Presenter(model, view, interactor, code)
            presenter.Delegate = self._presenter
            if code not in self._presenters:
                self._presenters[code] = [presenter]
            else:
                self._presenters[code] += [presenter]
        else:
            presenter.BringToFront()

        presenter.Keywords = None
        if keywords is None and shouldHighlight:
            presenter.Keywords = self._presenter.Model.Keywords
        elif keywords is not None and shouldHighlight:
            presenter.Keywords = keywords

        presenter.OpenBook(volume, page, section, selectItem=True, showBookList=showBookList)
        return presenter

    def OnReadWindowClose(self, code, presenter):
        if code in self._presenters:
            self._presenters[code].remove(presenter)
            if len(self._presenters[code]) == 0:
                del self._presenters[code]

def excepthook(type, value, tb):
    message = '%s Uncaught exception:\n' % (datetime.datetime.now())
    message += ''.join(traceback.format_exception(type, value, tb))
    with open(constants.ERROR_LOG_PATH, 'a') as log:
        log.write(message+'\n')
    print(message)

class MyApp(wx.App):

    def OnInit(self):
        mfs = wx.MemoryFSHandler()
        noteImage = wx.Bitmap(wx.Image(constants.NOTES_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        okImage = wx.Bitmap(wx.Image(constants.OK_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        notOkImage = wx.Bitmap(wx.Image(constants.NOT_OK_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        mfs.AddFile("edit-notes.png", noteImage, wx.BITMAP_TYPE_PNG)
        mfs.AddFile("ok.png", okImage, wx.BITMAP_TYPE_PNG)
        mfs.AddFile("not-ok.png", notOkImage, wx.BITMAP_TYPE_PNG)
        wx.FileSystem.AddHandler(mfs)
        return True

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        self.GetTopWindow().Raise()

def _ActivateOnMacOS():
    # A Python process launched from a terminal is not the active macOS
    # application, so its window opens behind the terminal. Tell the
    # NSApplication wxWidgets already created to activate itself.
    import ctypes, ctypes.util
    ctypes.cdll.LoadLibrary(ctypes.util.find_library('AppKit'))  # registers NSApplication
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    shared = objc.objc_msgSend(objc.objc_getClass(b'NSApplication'),
                               objc.sel_registerName(b'sharedApplication'))
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
    objc.objc_msgSend(shared, objc.sel_registerName(b'activateIgnoringOtherApps:'), True)

utils.MoveOldUserData()

sys.excepthook = excepthook

wx.Log.SetLogLevel(wx.LOG_FatalError)

app = MyApp(redirect=False, clearSigInt=True, useBestVisual=True)

# wxPython 4.2 added strict sizer consistency assertions that abort on
# mis-parented widgets and EXPAND/alignment flag combinations. This app ran
# fine under wxPython 4.0 with those quirks; keep the lenient behaviour so a
# latent quirk cannot crash the app at runtime.
wx.SizerFlags.DisableConsistencyChecks()

# Register the bundled fonts for this process so the app does not depend on
# the user installing them system-wide.
for _font_path in glob.glob(os.path.join(constants.FONTS_DIR, '*.ttf')):
    wx.Font.AddPrivateFont(_font_path)

parent = ParentFrame(None)
parent.PostInit()

parent.Show(True)

parent.StartAutoUpdateCheck()

if sys.platform == 'darwin':
    def _BringToFront():
        try:
            _ActivateOnMacOS()
        except Exception:
            traceback.print_exc()
        parent.Raise()
    wx.CallAfter(_BringToFront)

app.MainLoop()

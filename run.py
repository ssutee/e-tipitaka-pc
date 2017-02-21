#!/usr/bin/env python

import os, sys, traceback, datetime
import constants

if not os.path.exists(constants.DATA_PATH):
    os.makedirs(constants.DATA_PATH)

if not os.path.exists(constants.LOG_PATH):
    os.makedirs(constants.LOG_PATH)

import utils, settings

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

try:
    import wx.aui as aui
except ImportError,e:
    import wx.lib.agw.aui as aui

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
        icon.AddIconFromFile(constants.ICON_IMAGE, wx.BITMAP_TYPE_ANY)
        self.SetIcons(icon)

        self.Bind(wx.EVT_CLOSE, self.OnFrameClose)
        self._CreateStatusBar()

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
        self._progressBar.SetBezelFace(3)
        self._progressBar.SetShadowWidth(3)
        self._progressBar.SetRect(self._statusBar.GetFieldRect(3))

    def PositionProgressBar(self):
        if self: self._progressBar.SetRect(self._statusBar.GetFieldRect(3))

    def PostInit(self):
        self._statusBar.Bind(wx.EVT_SIZE, lambda event: wx.CallAfter(self.PositionProgressBar))

    def OnFrameClose(self, event):
        self._presenter._canBeClosed = True
        utils.SaveSearchWindowPosition(self)
        if self._presenter: self._presenter.SaveSearches()
        for code in self._presenters:
            self._presenter.SaveHistory(code)
        for child in self.GetClientWindow().GetChildren():
            if isinstance(child, aui.AuiMDIChildFrame):
                try:
                    child.Close()
                except wx.PyAssertionError,e:
                    pass
        event.Skip()

    def ReadAndCompare(self, code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords, code2, volume2, page2, keywords2):
        presenter = self.Read(code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords)
        index = presenter.View.AddReadPanel(code2)
        presenter.OpenAnotherBook(code2, index, volume2, page2, keywords2)


    def Read(self, code, volume, page, section, shouldHighlight, showBookList, shouldOpenNewWindow, keywords=None):
        presenter = None if self._presenters.get(code) is None else self._presenters.get(code)[0]

        if not presenter or shouldOpenNewWindow:
            model = read.model.Model(code)
            view = read.view.View(self, u'%s'%(utils.ShortName(code)), code)
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
    print message

class MyApp(wx.App):

    def OnInit(self):
        mfs = wx.MemoryFSHandler()
        noteImage = wx.BitmapFromImage(wx.Image(constants.NOTES_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        okImage = wx.BitmapFromImage(wx.Image(constants.OK_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        notOkImage = wx.BitmapFromImage(wx.Image(constants.NOT_OK_IMAGE, wx.BITMAP_TYPE_PNG).Scale(24,24))
        mfs.AddFile("edit-notes.png", noteImage, wx.BITMAP_TYPE_PNG)
        mfs.AddFile("ok.png", okImage, wx.BITMAP_TYPE_PNG)
        mfs.AddFile("not-ok.png", notOkImage, wx.BITMAP_TYPE_PNG)
        wx.FileSystem_AddHandler(mfs)        
        return True

utils.MoveOldUserData()

sys.excepthook = excepthook

wx.Log.SetLogLevel(wx.LOG_FatalError)

app = MyApp(redirect=False, clearSigInt=True, useBestVisual=True)

parent = ParentFrame(None)
parent.PostInit()

parent.Show()

app.MainLoop()

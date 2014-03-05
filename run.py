#!/usr/bin/env python

import os, sys
import constants

if not os.path.exists(constants.DATA_PATH):
    os.makedirs(constants.DATA_PATH)

import search.view
import search.interactor
import search.presenter
import search.model

import wx

wx.Log.SetLogLevel(0)

view = search.view.View()
interactor = search.interactor.Interactor()
model = search.model.ThaiRoyalSearchModel(None)  

presenter = search.presenter.Presenter(model, view, interactor)


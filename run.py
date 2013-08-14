#!/usr/bin/env python

import search.view
import search.interactor
import search.presenter
import search.model

import os, sys

view = search.view.View()
interactor = search.interactor.Interactor()
model = search.model.Model()

search.presenter.Presenter(model, view, interactor)

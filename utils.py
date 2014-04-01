#-*- coding:utf-8 -*-

import wx
import os, codecs, json
import constants

def ConvertToPaliSearch(search, force=False):
    return search.replace(u'ฐ', u'\uf700').replace(u'ญ', u'\uf70f').replace(u'\u0e4d', u'\uf711') if force or 'wxMac' not in wx.PlatformInfo else search

def ConvertToThaiSearch(search, force=False):
    return search.replace(u'\uf700', u'ฐ').replace(u'\uf70f', u'ญ').replace(u'\uf711', u'\u0e4d') if force or 'wxMac' in wx.PlatformInfo else search

def ThaiToArabic(number):
    if isinstance(number, int):
        number = unicode(number)
    assert isinstance(number, unicode), "%r is not unicode" % (number)
    d_tha = u'๐๑๒๓๔๕๖๗๘๙'
    d_arb = u'0123456789'
    result = ''
    for c in number:
        if c in d_tha:
            result += d_arb[d_tha.find(c)]
        else:
            result += c
    return result

def ArabicToThai(number):
    if isinstance(number, int):
        number = unicode(number)        
    assert isinstance(number, unicode), "%r is not unicode" % (number)
    d_tha = u'๐๑๒๓๔๕๖๗๘๙'
    d_arb = u'0123456789'
    result = ''
    for c in number:
        if c in d_arb:
            result += d_tha[d_arb.find(c)]
        else:
            result += c
    return result

def SaveFont(font, path, code=None):
    t = u'%s,%d,%d,%d,%d' % (font.GetFaceName(),font.GetFamily(),font.GetStyle(),font.GetWeight(),font.GetPointSize())
    path = path if code is None else path + '.' + code
    with codecs.open(path,'w','utf8') as f:
        f.write(t)        

def LoadFont(path, code=None):
    font = wx.Font(24, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
    font.SetFaceName(constants.DEFAULT_FONT)
    path = path if code is None else path + '.' + code    
    if not os.path.exists(path):
        return font

    with codecs.open(path,'r','utf8') as f:    
        tokens = f.read().split(',')
        if len(tokens) == 5:    
            font = wx.Font(int(tokens[4]),int(tokens[1]),int(tokens[2]),int(tokens[3]))
            font.SetFaceName(tokens[0])

    return font

def SaveWindowPosition(view, filename):
    if not os.path.exists(constants.CONFIG_PATH):
        os.mkdir(constants.CONFIG_PATH)

    with open(filename, 'w') as f:
        rect = view.GetScreenRect()
        displaySize = wx.GetDisplaySize()
        json.dump(((rect[0], rect[1], rect[2], rect[3]), (displaySize[0], displaySize[1])), f)

def SaveSearchWindowPosition(view):
    SaveWindowPosition(view, constants.SEARCH_RECT)
    
def SaveReadWindowPosition(view):
    SaveWindowPosition(view, constants.READ_RECT)

def LoadWindowPosition(filename):
    if not os.path.exists(filename):
        return None

    with open(filename) as f:
        try:
            rect, savedScreen = json.load(f)
            currentScreen = wx.GetDisplaySize()
            xScale, yScale = 1.0*savedScreen[0]/currentScreen[0], 1.0*savedScreen[1]/currentScreen[1]
        except ValueError, e:
            return None

    if type(rect) is list and len(rect) == 4:
        return rect if xScale == 1 and yScale == 1 else [currentScreen[0]/4, currentScreen[1]/4, currentScreen[0]/2, currentScreen[1]/2]
        
    return None


def LoadReadWindowPosition():
    return LoadWindowPosition(constants.READ_RECT)
    
def LoadSearchWindowPosition():
    return LoadWindowPosition(constants.SEARCH_RECT)


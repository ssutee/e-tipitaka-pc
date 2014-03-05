#-*- coding:utf-8 -*-

import wx
import os, codecs
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

#-*- coding:utf-8 -*-

import wx
import os, codecs

def ConvertToPaliSearch(search):
    return search.replace(u'ฐ', u'\uf700').replace(u'ญ', u'\uf70f').replace(u'\u0e4d', u'\uf711')

def ThaiToArabic(number):
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

def SaveFont(font, path):
    t = u'%s,%d,%d,%d,%d' % (font.GetFaceName(),font.GetFamily(),font.GetStyle(),font.GetWeight(),font.GetPointSize())
    with codecs.open(path,'w','utf8') as f:
        f.write(t)        

def LoadFont(path):
    if not os.path.exists(path):
        return None        

    font = None
    with codecs.open(path,'r','utf8') as f:    
        tokens = f.read().split(',')
        if len(tokens) == 5:    
            font = wx.Font(int(tokens[4]),int(tokens[1]),int(tokens[2]),int(tokens[3]))
            font.SetFaceName(tokens[0])
    return font


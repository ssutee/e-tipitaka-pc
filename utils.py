#-*- coding:utf-8 -*-

def ConvertToPaliSearch(search):
    return search.replace(u'ฐ', u'\uf700').replace(u'ญ', u'\uf70f').replace(u'\u0e4d', u'\uf711')
    

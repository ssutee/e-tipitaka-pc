#-*- coding:utf-8 -*-

import os, os.path, sys, cPickle
from os.path import expanduser

from whoosh.spelling import SpellChecker
from whoosh.filedb.filestore import FileStorage
from whoosh.index import open_dir

HOME = expanduser("~")

LANG_THAI = 'thai'
LANG_PALI = 'pali'

DEFAULT_FONT = 'TF Chiangsaen'

ITEMS_PER_PAGE = 20

MODE_ALL = 0
MODE_CUSTOM = 1

CONFIG_PATH = os.path.join(HOME, 'E-Tipitaka','config')
LOG_FILE = os.path.join(CONFIG_PATH,'history.log')

SEARCH_FONT = os.path.join(CONFIG_PATH, 'font_search.log')
READ_FONT = os.path.join(CONFIG_PATH, 'font_read.log')

SEARCH_IMAGE = os.path.join('resources','search.png')
NIKHAHIT_IMAGE = os.path.join('resources','nikhahit.gif')
THOTHAN_IMAGE = os.path.join('resources','thothan.gif')
YOYING_IMAGE = os.path.join('resources','yoying.gif')
FONTS_IMAGE = os.path.join('resources','fonts.png')
LEFT_IMAGE = os.path.join('resources','left.png')
RIGHT_IMAGE = os.path.join('resources','right.png')
IMPORT_IMAGE = os.path.join('resources','import.png')
EXPORT_IMAGE = os.path.join('resources','export.png')
BOOKS_IMAGE = os.path.join('resources','books.png')
ICON_IMAGE = os.path.join('resources','e-tri_64_icon.ico')

THAI_FIVE_BOOKS_DB = os.path.join('resources','thaibt.db')
THAI_ROYAL_DB = os.path.join('resources','thai.db')
THAI_MAHACHULA_DB = os.path.join('resources','thaimc.db')
THAI_MAHAMAKUT_DB = os.path.join('resources','thaimm.db')
PALI_SIAM_DB = os.path.join('resources','pali.db')

THAI_FIVE_BOOKS_CODE = 'thaibt'
THAI_ROYAL_CODE = 'thai'
THAI_MAHACHULA_CODE = 'thaimc'
THAI_MAHAMAKUT_CODE = 'thaimm'
PALI_SIAM_CODE = 'pali'

THAI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join('resources', 'spell_thai')))
PALI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join('resources', 'spell_pali')))

BOOK_NAMES = cPickle.load(open(os.path.join('resources','book_name.pkl'),'rb'))

FIVE_BOOKS_NAMES = [
    u'ขุมทรัพย์จากพระโอษฐ์', 
    u'อริยสัจจากพระโอษฐ์ ๑', 
    u'อริยสัจจากพระโอษฐ์ ๒', 
    u'ปฏิจจสมุปบาทจากพระโอษฐ์', 
    u'พุทธประวัติจากพระโอษฐ์']

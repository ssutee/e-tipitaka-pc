#-*- coding:utf-8 -*-

import wx
import os, os.path, sys, cPickle, json
from os.path import expanduser

from whoosh.spelling import SpellChecker
from whoosh.filedb.filestore import FileStorage
from whoosh.index import open_dir
from appdirs import user_data_dir, user_log_dir


APP_NAME = 'E-Tipitaka'
APP_AUTHOR = 'Sutee'

VIRTURE_STORE = user_data_dir('VirtualStore', '')

HOME = expanduser("~")

CODES = ['thai', 'pali', 'thaiwn', 'thaimm', 'thaimc', 'thaipb', 'thaibt', 'romanct']
COMPARE_CODES = ['thai', 'pali', 'thaiwn', 'thaimm', 'thaimc', 'romanct']
COMPARE_CHOICES = [u'ไทย (ฉบับหลวง)', u'บาลี (สยามรัฐ)', u'พุทธวจนปิฎก', u'ไทย (มหามกุฏฯ)', u'ไทย (มหาจุฬาฯ)', u'Roman Script']

LANG_THAI = 'thai'
LANG_PALI = 'pali'

SEARCH = 'search'
READ = 'read'

DEFAULT_FONT = 'TF Chiangsaen'
ROMAN_SCRIPT_DEFAULT_FONT = 'Times New Roman'

ITEMS_PER_PAGE = 20

FOOTER_STYLE = '#3CBF3F', 4

ETZ_TYPE = u'E-Tipitaka Backup File (*.etz;*.js)|*.etz;*.js'
IOS_ETZ_TYPE = u'iOS Backup File (*.json.etz)|*.json.etz'
ANDROID_ETZ_TYPE = u'Android Backup File (*.js)|*.js'

CHECK_VERSION_URL   = 'http://download.watnapahpong.org/data/etipitaka/version.txt'

DOWNLOAD_MSW_URL     = 'http://download.watnapahpong.org/data/E-Tipitaka-latest.exe'
DOWNLOAD_OSX_URL     = 'http://download.watnapahpong.org/data/E-Tipitaka-latest.dmg'
DOWNLOAD_SRC_URL     = 'http://download.watnapahpong.org/data/E-Tipitaka-latest.tar.gz'

PALI_PDF_URL_PATTERN = "http://pali.watnapp.com/?volume=%d&start=%d&end=%d"

CMD_IDLE            = 1000
CMD_FORWARD         = 1001
CMD_BACKWARD        = 1002
CMD_JUMP_TO_PAGE    = 1003
CMD_JUMP_TO_ITEM    = 1004
CMD_JUMP_TO_VOLUME  = 1005
CMD_ZOOM_IN         = 1006
CMD_ZOOM_OUT        = 1007
CMD_FIND            = 1008
CMD_COPY_REFERENCE  = 1009

ID_COPY           = 2000
ID_SELECT_ALL     = 2001
ID_SEARCH         = 2002
ID_COPY_REFERENCE = 2003

UP      = 0
DOWN    = 1

MODE_ALL    = 0
MODE_CUSTOM = 1

NIKHAHIT_CHAR   = u'\uf711'
THOTHAN_CHAR    = u'\uf700'
YOYING_CHAR     = u'\uf70f'

RESOURCES_DIR = 'resources'
NOTES_DIR = 'notes'
MARKS_DIR = 'marks'
BOOKMARKS_DIR = 'favs'
CONFIG_DIR = 'config'

OLD_DATA_PATH = os.path.join(HOME, '.' + APP_NAME)

DATA_PATH = user_data_dir(APP_NAME, APP_AUTHOR)
LOG_PATH = user_log_dir(APP_NAME, APP_AUTHOR)

NOTES_PATH = os.path.join(DATA_PATH, NOTES_DIR)
MARKS_PATH = os.path.join(DATA_PATH, MARKS_DIR)
BOOKMARKS_PATH = os.path.join(DATA_PATH, BOOKMARKS_DIR)

ERROR_LOG_PATH = os.path.join(LOG_PATH, 'error.log')

CONFIG_PATH = os.path.join(DATA_PATH, CONFIG_DIR)
LOG_FILE = os.path.join(CONFIG_PATH, 'history.log')
SKIP_VERSION_FILE = os.path.join(CONFIG_PATH, 'skip_version')
IMPORTED_MARK_FILE = os.path.join(DATA_PATH, 'imported_old_user_data')

SEARCH_FONT = os.path.join(CONFIG_PATH, 'font_search.cfg')
READ_FONT = os.path.join(CONFIG_PATH, 'font_read.cfg')
SEARCH_RECT = os.path.join(CONFIG_PATH, 'rect_search.cfg')
READ_RECT = os.path.join(CONFIG_PATH, 'rect_read.cfg')

THEME_CFG = os.path.join(CONFIG_PATH, 'theme.cfg')
NOTE_STATUS_CFG = os.path.join(CONFIG_PATH, 'comment.cfg')

SEARCH_IMAGE = os.path.join(RESOURCES_DIR, 'search.png')
NIKHAHIT_IMAGE = os.path.join(RESOURCES_DIR, 'nikhahit.gif')
THOTHAN_IMAGE = os.path.join(RESOURCES_DIR, 'thothan.gif')
YOYING_IMAGE = os.path.join(RESOURCES_DIR, 'yoying.gif')
FONTS_IMAGE = os.path.join(RESOURCES_DIR, 'fonts.png')
LEFT_IMAGE = os.path.join(RESOURCES_DIR, 'left.png')
RIGHT_IMAGE = os.path.join(RESOURCES_DIR, 'right.png')
READ_IMAGE = os.path.join(RESOURCES_DIR, 'read.png')
IMPORT_IMAGE = os.path.join(RESOURCES_DIR, 'import.png')
EXPORT_IMAGE = os.path.join(RESOURCES_DIR, 'export.png')
BOOKS_IMAGE = os.path.join(RESOURCES_DIR, 'books.png')
ICON_IMAGE = os.path.join(RESOURCES_DIR, 'e-tri_64_icon.ico')
KEY_ENTER_IMAGE = os.path.join(RESOURCES_DIR, 'key_enter.png')
FILE_DELETE_IMAGE = os.path.join(RESOURCES_DIR, 'file_delete.png')

STAR_IMAGE = os.path.join(RESOURCES_DIR, 'star.png')
NOTES_IMAGE = os.path.join(RESOURCES_DIR, 'edit-notes.png')
DICT_IMAGE = os.path.join(RESOURCES_DIR, 'dict.png')
THAI_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'thaidict.png')
PALI_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'palidict.png')
ENGLISH_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'palieng.png')
DICT_ICON = os.path.join(RESOURCES_DIR, 'dict.ico')
LAYOUT_IMAGE = os.path.join(RESOURCES_DIR, 'layout.gif')
INC_IMAGE = os.path.join(RESOURCES_DIR, 'fontSizeUp.gif')
DEC_IMAGE = os.path.join(RESOURCES_DIR,'fontSizeDown.gif')
SAVE_IMAGE = os.path.join(RESOURCES_DIR, 'save.png')
PRINT_IMAGE = os.path.join(RESOURCES_DIR, 'print.png')
YELLOW_IMAGE = os.path.join(RESOURCES_DIR, 'yellow.png')
WHITE_IMAGE = os.path.join(RESOURCES_DIR, 'white.png')
CLEAR_IMAGE = os.path.join(RESOURCES_DIR, 'clear.png')
ABOUT_IMAGE = os.path.join(RESOURCES_DIR, 'about.png')
HEADER_IMAGE = os.path.join(RESOURCES_DIR, 'header.png')

DATA_DB = os.path.join(DATA_PATH, 'data.sqlite')
NOTE_DB = os.path.join(DATA_PATH, 'note.sqlite')

THAI_FIVE_BOOKS_DB = os.path.join(RESOURCES_DIR, 'thaibt.db')
THAI_ROYAL_DB = os.path.join(RESOURCES_DIR, 'thai.db')
THAI_MAHACHULA_DB = os.path.join(RESOURCES_DIR, 'thaimc.db')
THAI_MAHAMAKUT_DB = os.path.join(RESOURCES_DIR, 'thaimm.db')
THAI_SCRIPT_DB = os.path.join(RESOURCES_DIR, 'thaict.db')
ROMAN_SCRIPT_DB = os.path.join(RESOURCES_DIR, 'romanct.db')
THAI_WATNA_DB = os.path.join(RESOURCES_DIR, 'thaiwn.db')
THAI_POCKET_BOOK_DB = os.path.join(RESOURCES_DIR, 'thaipb.db')

PALI_SIAM_DB = os.path.join(RESOURCES_DIR, 'pali.db')

PALI_DICT_DB = os.path.join(RESOURCES_DIR, 'p2t_dict.db')
THAI_DICT_DB = os.path.join(RESOURCES_DIR, 'thaidict.db')
ENGLISH_DICT_DB = os.path.join(RESOURCES_DIR, 'pali-english.db')

THAI_FIVE_BOOKS_CODE = 'thaibt'
THAI_ROYAL_CODE = 'thai'
THAI_MAHACHULA_CODE = 'thaimc'
THAI_MAHAMAKUT_CODE = 'thaimm'
PALI_SIAM_CODE = 'pali'
THAI_SCRIPT_CODE = 'thaict'
ROMAN_SCRIPT_CODE = 'romanct'
THAI_WATNA_CODE = 'thaiwn'
THAI_POCKET_BOOK_CODE = 'thaipb'

THAI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_thai')))
PALI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_pali')))

BOOK_NAMES = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_name.pkl'), 'rb'))
BOOK_PAGES = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_page.pkl'),  'rb'))
BOOK_ITEMS = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_item.pkl'),  'rb'))
VOLUME_TABLE = cPickle.load(open(os.path.join(RESOURCES_DIR, 'maps.pkl'),  'rb'))
SCRIPT_ITEMS = json.loads(open(os.path.join(RESOURCES_DIR, 'ct_items.json')).read())

MAP_MC_TO_SIAM = cPickle.load(open(os.path.join(RESOURCES_DIR, 'mc_map.pkl'), 'rb'))

FIVE_BOOKS_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'bt_toc.json')).read())

ROMAN_SCRIPT_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'toc_rm.json')).read())
THAI_SCRIPT_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'toc_th.json')).read())

ROMAN_SCRIPT_TITLES = json.loads(open(os.path.join(RESOURCES_DIR, 'titles_rm.json')).read())
THAI_SCRIPT_TITLES = json.loads(open(os.path.join(RESOURCES_DIR, 'titles_th.json')).read())

ROMAN_BOOK_NAMES = open(os.path.join(RESOURCES_DIR, 'roman_names.txt')).readlines()
ROMAN_MAPPING_TABLE = json.loads(open(os.path.join(RESOURCES_DIR, 'map_cst.json')).read())
ROMAN_REVERSE_MAPPING_TABLE = json.loads(open(os.path.join(RESOURCES_DIR, 'map_cst_r.json')).read())
ROMAN_PAGE_INDEX = json.loads(open(os.path.join(RESOURCES_DIR, 'roman_page_index.json')).read())
ROMAN_ITEMS = json.loads(open(os.path.join(RESOURCES_DIR, 'roman_items.json')).read())

FIVE_BOOKS_NAMES = [
    u'ขุมทรัพย์จากพระโอษฐ์', 
    u'อริยสัจจากพระโอษฐ์ ๑', 
    u'อริยสัจจากพระโอษฐ์ ๒', 
    u'ปฏิจจสมุปบาทจากพระโอษฐ์', 
    u'พุทธประวัติจากพระโอษฐ์']

FIVE_BOOKS_PAGES = {
    1:466,
    2:817,
    3:1572,
    4:813,
    5:614,
}

SECTION_THAI_NAMES = [
    u'พระวินัยปิฎก', u'พระสุตตันตปิฎก', u'พระอภิธรรมปิฎก'
]

SECTION_PALI_NAMES = [
    u'วินยปิฏเก', u'สุตฺตนฺตปิฏเก', u'อภิธมฺมปิฏเก'
]

FIVE_BOOKS_SECTIONS = {
    1:[
        u'',
        u'หมวดที่ ๑ ว่าด้วย การทุศีล',
        u'หมวดที่ ๒ ว่าด้วย การไม่สังวร',
        u'หมวดที่ ๓ ว่าด้วย เกียรติและลาภสักการะ',
        u'หมวดที่ ๔ ว่าด้วย การทำไปตามอำนาจกิเลส',
        u'หมวดที่ ๕ ว่าด้วย การเป็นทาสตัณหา',
        u'หมวดที่ ๖ ว่าด้วย การหละหลวมในธรรม',
        u'หมวดที่ ๗ ว่าด้วย การลืมคำปฏิญาณ',
        u'หมวดที่ ๘ ว่าด้วย พิษสงทางใจ',
        u'หมวดที่ ๙ ว่าด้วย การเสียความเป็นผู้หลักผู้ใหญ่',
        u'หมวดที่ ๑๐ ว่าด้วย การมีศีล',
        u'หมวดที่ ๑๑ ว่าด้วย การมีสังวร',
        u'หมวดที่ ๑๒ ว่าด้วย การเป็นอยู่ชอบ',
        u'หมวดที่ ๑๓ ว่าด้วย การไม่ทำไปตามอำนาจกิเลส',
        u'หมวดที่ ๑๔ ว่าด้วย การไม่เป็นทาสตัณหา',
        u'หมวดที่ ๑๕ ว่าด้วย การไม่หละหลวมในธรรม',
        u'หมวดที่ ๑๖ ว่าด้วย การไม่ลืมคำปฏิญาณ',
        u'หมวดที่ ๑๗ ว่าด้วย การหมดพิษสงทางใจ',
        u'หมวดที่ ๑๘ ว่าด้วย การไม่เสียความเป็นผู้หลักผู้ใหญ่',
        u'หมวดที่ ๑๙ ว่าด้วย เนื้อนาบุญของโลก',                                                            
    ], 
    2:[
        u'ภาคนำ ว่าด้วย ข้อความที่ควรทราบก่อนเกี่ยวกับจตุราริยสัจ',
        u'ภาค ๑ ว่าด้วย ทุกขอริยสัจ ความจริงอันประเสริฐคือทุกข์',
        u'ภาค ๒ ว่าด้วย สมุทยอริยสัจ ความจริงอันประเสริฐคือเหตุให้เกิดทุกข์',
        u'ภาค ๓ ว่าด้วย นิโรธอริยสัจ ความจริงอันประเสริฐคือความดับไม่เหลือของทุกข์',
    ], 
    3:[
        u'',
        u'',
        u'',
        u'',
        u'ภาค ๔ ว่าด้วย มัคคอริยสัจ ความจริงอันประเสริฐคือมรรค',
        u'ภาคผนวก ว่าด้วย เรื่องนำมาผนวก เพื่อความสะดวกแก่การอ้างอิงสำหรับเรื่องที่ตรัสซ้ำ ๆ บ่อย ๆ',
    ], 
    4:[
        u'บทนำ ว่าด้วย เรื่องที่ควรทราบก่อนเกี่ยวกับปฏิจจสมุปบาท',
        u'หมวด ๑ ว่าด้วย ลักษณะ – ความสำคัญ – วัตถุประสงค์ของเรื่องปฏิจจสมุปบาท',
        u'หมวด ๒ ว่าด้วย ปฏิจจสมุปบาทคืออริยสัจสมบูรณ์แบบ',
        u'หมวด ๓ ว่าด้วย บาลีแสดงว่าปฏิจจสมุปบาทไม่ใช่เรื่องข้ามภพข้ามชาติ',
        u'หมวด ๔ ว่าด้วย ปฏิจจสมุปบาทเกิดได้เสมอในชีวิตประจำวันของคนเรา',
        u'หมวด ๕ ว่าด้วย ปฏิจจสมุปบาทซึ่งแสดงการเกิดดับแห่งกิเลสและความทุกข์',
        u'หมวด ๖ ว่าด้วย ปฏิจจสมุปบาทที่ตรัสในรูปของการปฏิบัติ',
        u'หมวด ๗ ว่าด้วย โทษของการไม่รู้และอานิสงส์ของการรู้ปฏิจจสมุปบาท',
        u'หมวด ๘ ว่าด้วย ปฏิจจสมุปบาทเกี่ยวกับความเป็นพระพุทธเจ้า',
        u'หมวด ๙ ว่าด้วย ปฏิจจสมุปบาทกับอริยสาวก',
        u'หมวด ๑๐ ว่าด้วย ปฏิจจสมุปบาทนานาแบบ',
        u'หมวด ๑๑ ว่าด้วย ลัทธิหรือทิฏฐิที่ขัดกับปฏิจจสมุปบาท',
        u'หมวด ๑๒ ว่าด้วย ปฏิจจสมุปบาทที่ส่อไปในทางภาษาคน - เพื่อศีลธรรม',
        u'บทสรุป ว่าด้วย คุณค่าพิเศษของปฏิจจสมุปบาท',
    ], 
    5:[
        u'ภาคนำ ข้อความให้เกิดความสนใจในพุทธประวัติ',
        u'ภาค ๑ เริ่มแต่การเกิดแห่งวงศ์สากยะ, เรื่องก่อนประสูติ, จนถึงออกผนวช',
        u'ภาค ๒ เริ่มแต่ออกผนวชแล้วเที่ยวเสาะแสวงหาความรู้ ทรมานพระองค์ จนได้ตรัสรู้',
        u'ภาค ๓ เริ่มแต่ตรัสรู้แล้วทรงประกอบด้วยพระคุณธรรมต่าง ๆ จนเสด็จไปโปรดปัญจวัคคีย์บรรลุผล',
        u'ภาค ๔ เรื่องเบ็ดเตล็ดใหญ่น้อยต่าง ๆ ตั้งแต่โปรดปัญจวัคคีย์แล้ว  ไปจนถึงจวนจะปรินิพพาน',
        u'ภาค ๕ การปรินิพพาน',
        u'ภาค ๖ เรื่องการบำเพ็ญบารมีในอดีตชาติ ซึ่งเต็มไปด้วยทิฏฐานุคติอันสาวกในภายหลังพึงดำเนินตาม',
    ]} 

XML_NOTE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<richtext version="1.0.0.0" xmlns="http://www.wxwidgets.org">
  <paragraphlayout textcolor="#000000" fontpointsize="13" fontfamily="70" fontstyle="90" fontweight="90" fontunderlined="0" fontface="Lucida Grande" alignment="1" parspacingafter="10" parspacingbefore="0" linespacing="10" margin-left="5,4098" margin-right="5,4098" margin-top="5,4098" margin-bottom="5,4098">
  </paragraphlayout>
</richtext>    
'''

IOS_CODE_TABLE = {
    1: 'thai',
    2: 'pali',
    3: 'thaimm',
    4: 'thaimc',
    5: 'thaibt',
    6: 'thaiwn',
    7: 'thaipb',
    8: 'romanct',
}

ANDROID_CODE_TABLE = {
    0: 'thai',
    1: 'pali',
    2: 'thaimm',
    3: 'thaimc',
    4: 'thaibt',
    5: 'thaiwn',
    6: 'thaipb',
    7: 'romanct',    
}
#-*- coding:utf-8 -*-

import os, os.path, sys, cPickle, json
from os.path import expanduser

from whoosh.spelling import SpellChecker
from whoosh.filedb.filestore import FileStorage
from whoosh.index import open_dir

APP_NAME = 'E-Tipitaka'

HOME = expanduser("~")

CODES = ['thai', 'pali', 'thaimm', 'thaimc', 'thaibt']

LANG_THAI = 'thai'
LANG_PALI = 'pali'

DEFAULT_FONT = 'TF Chiangsaen'

ITEMS_PER_PAGE = 20

FOOTER_STYLE = '#3CBF3F', 4

ETZ_TYPE = u'E-Tipitaka Backup File (*.etz)|*.etz'

CMD_IDLE            = 1000
CMD_FORWARD         = 1001
CMD_BACKWARD        = 1002
CMD_JUMP_TO_PAGE    = 1003
CMD_JUMP_TO_ITEM    = 1004
CMD_JUMP_TO_VOLUME  = 1005
CMD_ZOOM_IN         = 1006
CMD_ZOOM_OUT        = 1007
CMD_FIND            = 1008

UP      = 0
DOWN    = 1

MODE_ALL = 0
MODE_CUSTOM = 1

NIKHAHIT_CHAR = u'\uf711'
THOTHAN_CHAR = u'\uf700'
YOYING_CHAR = u'\uf70f'

RESOURCES_DIR = 'resources'
NOTES_DIR = 'notes'
MARKS_DIR = 'marks'
BOOKMARKS_DIR = 'favs'
CONFIG_DIR = 'config'

DATA_PATH = os.path.join(HOME, APP_NAME)
NOTES_PATH = os.path.join(DATA_PATH, NOTES_DIR)
MARKS_PATH = os.path.join(DATA_PATH, MARKS_DIR)
BOOKMARKS_PATH = os.path.join(DATA_PATH, BOOKMARKS_DIR)

CONFIG_PATH = os.path.join(DATA_PATH, CONFIG_DIR)
LOG_FILE = os.path.join(CONFIG_PATH, 'history.log')

SEARCH_FONT = os.path.join(CONFIG_PATH, 'font_search.cfg')
READ_FONT = os.path.join(CONFIG_PATH, 'font_read.cfg')

SEARCH_IMAGE = os.path.join(RESOURCES_DIR, 'search.png')
NIKHAHIT_IMAGE = os.path.join(RESOURCES_DIR, 'nikhahit.gif')
THOTHAN_IMAGE = os.path.join(RESOURCES_DIR, 'thothan.gif')
YOYING_IMAGE = os.path.join(RESOURCES_DIR, 'yoying.gif')
FONTS_IMAGE = os.path.join(RESOURCES_DIR, 'fonts.png')
LEFT_IMAGE = os.path.join(RESOURCES_DIR, 'left.png')
RIGHT_IMAGE = os.path.join(RESOURCES_DIR, 'right.png')
IMPORT_IMAGE = os.path.join(RESOURCES_DIR, 'import.png')
EXPORT_IMAGE = os.path.join(RESOURCES_DIR, 'export.png')
BOOKS_IMAGE = os.path.join(RESOURCES_DIR, 'books.png')
ICON_IMAGE = os.path.join(RESOURCES_DIR, 'e-tri_64_icon.ico')
KEY_ENTER_IMAGE = os.path.join(RESOURCES_DIR, 'key_enter.png')

STAR_IMAGE = os.path.join(RESOURCES_DIR, 'star.png')
DICT_IMAGE = os.path.join(RESOURCES_DIR, 'dict.png')
DICT_ICON = os.path.join(RESOURCES_DIR, 'dict.ico')
LAYOUT_IMAGE = os.path.join(RESOURCES_DIR, 'layout.gif')
INC_IMAGE = os.path.join(RESOURCES_DIR, 'fontSizeUp.gif')
DEC_IMAGE = os.path.join(RESOURCES_DIR,'fontSizeDown.gif')
SAVE_IMAGE = os.path.join(RESOURCES_DIR, 'save.png')
PRINT_IMAGE = os.path.join(RESOURCES_DIR, 'print.png')
YELLOW_IMAGE = os.path.join(RESOURCES_DIR, 'yellow.png')
WHITE_IMAGE = os.path.join(RESOURCES_DIR, 'white.png')
CLEAR_IMAGE = os.path.join(RESOURCES_DIR, 'clear.png')

DATA_DB = os.path.join(DATA_PATH, 'data.sqlite')

THAI_FIVE_BOOKS_DB = os.path.join(RESOURCES_DIR, 'thaibt.db')
THAI_ROYAL_DB = os.path.join(RESOURCES_DIR, 'thai.db')
THAI_MAHACHULA_DB = os.path.join(RESOURCES_DIR, 'thaimc.db')
THAI_MAHAMAKUT_DB = os.path.join(RESOURCES_DIR, 'thaimm.db')
PALI_SIAM_DB = os.path.join(RESOURCES_DIR, 'pali.db')
DICT_DB = os.path.join(RESOURCES_DIR, 'p2t_dict.db')

THAI_FIVE_BOOKS_CODE = 'thaibt'
THAI_ROYAL_CODE = 'thai'
THAI_MAHACHULA_CODE = 'thaimc'
THAI_MAHAMAKUT_CODE = 'thaimm'
PALI_SIAM_CODE = 'pali'

THAI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_thai')))
PALI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_pali')))

BOOK_NAMES = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_name.pkl'), 'rb'))
BOOK_PAGES = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_page.pkl'),  'rb'))
BOOK_ITEMS = cPickle.load(open(os.path.join(RESOURCES_DIR, 'book_item.pkl'),  'rb'))
VOLUME_TABLE = cPickle.load(open(os.path.join(RESOURCES_DIR, 'maps.pkl'),  'rb'))

MAP_MC_TO_SIAM = cPickle.load(open(os.path.join(RESOURCES_DIR, 'mc_map.pkl'), 'rb'))

FIVE_BOOKS_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'bt_toc.json')).read())

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
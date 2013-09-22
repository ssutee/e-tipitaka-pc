#-*- coding:utf-8 -*-

import os, os.path, sys, cPickle, json
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

STAR_IMAGE = os.path.join('resources','star.png')
DICT_IMAGE = os.path.join('resources','dict.png')
LAYOUT_IMAGE = os.path.join('resources','layout.gif')
INC_IMAGE = os.path.join('resources','fontSizeUp.gif')
DEC_IMAGE = os.path.join('resources','fontSizeDown.gif')
SAVE_IMAGE = os.path.join('resources','save.png')
PRINT_IMAGE = os.path.join('resources','print.png')

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
BOOK_PAGES = cPickle.load(open(os.path.join('resources','book_page.pkl'), 'rb'))
BOOK_ITEMS = cPickle.load(open(os.path.join('resources','book_item.pkl'), 'rb'))

FIVE_BOOKS_TOC = json.loads(open(os.path.join('resources','bt_toc.json')).read())

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
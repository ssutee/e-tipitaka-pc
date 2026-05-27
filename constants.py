#-*- coding:utf-8 -*-

import wx
import os, os.path, sys, pickle, json
from os.path import expanduser

from whoosh.spelling import SpellChecker
from whoosh.filedb.filestore import FileStorage
from whoosh.index import open_dir
from appdirs import user_data_dir, user_log_dir
from utils import GetUserDataDir

APP_NAME = 'E-Tipitaka'
APP_AUTHOR = 'Sutee'

VIRTURE_STORE = user_data_dir('VirtualStore', '')

HOME = expanduser("~")

THAI_FIVE_BOOKS_CODE = 'thaibt'
THAI_ROYAL_CODE = 'thai'
THAI_MAHACHULA_CODE = 'thaimc'
THAI_MAHACHULA2_CODE = 'thaimc2'
PALI_MAHACHULA_CODE = 'palimc'
THAI_MAHAMAKUT_CODE = 'thaimm'
PALI_SIAM_CODE = 'pali'
PALI_SIAM_NEW_CODE = 'palinew'
THAI_SCRIPT_CODE = 'thaict'
ROMAN_SCRIPT_CODE = 'romanct'
THAI_WATNA_CODE = 'thaiwn'
THAI_POCKET_BOOK_CODE = 'thaipb'
THAI_SUPREME_CODE = 'thaims'
THAI_VINAYA_CODE = 'thaivn'

#          0        1        2        3         4         5         6          7         8          9          10       11         12
CODES = ['thai', 'pali', 'thaiwn', 'thaimm', 'thaimc', 'thaipb', 'thaibt', 'romanct', 'palimc', 'thaims', 'thaivn', 'palinew', 'thaimc2']

COMPARE_CHOICES = ['ไทย (ฉบับหลวง)', 'บาลี (สยามรัฐ พ.ศ.๒๕๓๘)', 'บาลี (สยามรัฐ พ.ศ.๒๔๗๐)',
                   'พุทธวจนปิฎก ๓๓ เล่ม', 'ไทย (มหามกุฏฯ)', 'ไทย (มหาจุฬาฯ ๑)', 'ไทย (มหาจุฬาฯ ๒)', 'ไทย (เฉลิมพระเกียรติ ๒๕๔๙)', 'บาลี (มหาจุฬาฯ)', 'Roman Script']
COMPARE_ORDER = [0,1,11,2,3,4,12,9,8,7]

LANGS = ['ไทย (ฉบับหลวง)', 'บาลี (สยามรัฐ พ.ศ.๒๕๓๘)', 'บาลี (สยามรัฐ พ.ศ.๒๔๗๐)', 'พุทธวจนปิฎก ๓๓ เล่ม', 'ไทย (มหามกุฏฯ)', 'ไทย (มหาจุฬาฯ ๑)', 'ไทย (มหาจุฬาฯ ๒)', 'ไทย (เฉลิมพระเกียรติ ๒๕๔๙)', 'บาลี (มหาจุฬาฯ)', 'พุทธวจน หมวดธรรม', 'ชุดจากพระโอษฐ์ ๕ เล่ม', 'อริยวินัย', 'Roman Script']
LANGS_ORDER = [0,1,11,2,3,4,12,9,8,5,6,10,7]


# ---------------------------------------------------------------------------
# Build-time feature toggles (see build.toml.example).
#
# `build.toml` is read at import time. Missing file -> full release (include
# every code book). Currently only `features.include_thaiwn` is supported;
# setting it to false removes the thaiwn entry from the language combo and
# every code-selection list in the UI. The thaiwn.sqlite resource is still
# bundled by default unless the etipitaka.spec build also reads the same
# build.toml and filters it out (which it does).
# ---------------------------------------------------------------------------

def _load_build_config():
    try:
        import tomllib
    except ImportError:   # pragma: no cover -- Python <3.11
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    base = sys._MEIPASS if getattr(sys, 'frozen', False) \
        else os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'build.toml')
    try:
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except (OSError, FileNotFoundError):
        return {}


_BUILD_CONFIG = _load_build_config()
_features = _BUILD_CONFIG.get('features', {}) or {}

DISABLED_CODES = frozenset(
    code for code in (
        ('thaiwn' if not _features.get('include_thaiwn', True) else None),
    )
    if code is not None
)


def IS_CODE_ENABLED(code):
    return code not in DISABLED_CODES


def _filter_visible(order):
    return [o for o in order if IS_CODE_ENABLED(CODES[o])]


# Display-time filtered variants. UI sites use these in place of LANGS /
# LANGS_ORDER / COMPARE_ORDER so disabled codes never appear in pickers,
# combo boxes, or compare dialogs.
VISIBLE_LANGS_ORDER = _filter_visible(LANGS_ORDER)
VISIBLE_LANGS = [LANGS[LANGS_ORDER.index(o)] for o in VISIBLE_LANGS_ORDER]
VISIBLE_COMPARE_ORDER = _filter_visible(COMPARE_ORDER)
VISIBLE_COMPARE_CHOICES = [COMPARE_CHOICES[COMPARE_ORDER.index(o)] for o in VISIBLE_COMPARE_ORDER]

LANG_THAI = 'thai'
LANG_PALI = 'pali'

SEARCH = 'search'
READ = 'read'

DEFAULT_FONT = 'TF Chiangsaen' if wx.Port != '__WXGTK__' else 'Sans'
ROMAN_SCRIPT_DEFAULT_FONT = 'Times New Roman' if wx.Port != '__WXGTK__' else 'Sans'

ITEMS_PER_PAGE = 20

FOOTER_STYLE = '#3CBF3F', 4

ETZ_TYPE = 'E-Tipitaka Backup File (*.etz;*.js;*.json)|*.etz;*.js;*.json'

CHECK_VERSION_URL   = 'http://download.watnapahpong.org/data/etipitaka/version.txt'

DOWNLOAD_MSW_URL     = 'http://download.watnapahpong.org/data/E-Tipitaka-latest.exe'
DOWNLOAD_OSX_URL     = 'http://download.watnapahpong.org/data/E-Tipitaka-latest.pkg'
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
CMD_PRINT           = 1010
CMD_SAVE            = 1011

ID_COPY           = 2000
ID_SELECT_ALL     = 2001
ID_SEARCH         = 2002
ID_COPY_REFERENCE = 2003

UP      = 0
DOWN    = 1

MODE_ALL    = 0
MODE_CUSTOM = 1

NIKHAHIT_CHAR   = '\uf711'
THOTHAN_CHAR    = '\uf700'
YOYING_CHAR     = '\uf70f'

if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(_BASE_DIR, 'resources')
FONTS_DIR = os.path.join(_BASE_DIR, 'fonts')
NOTES_DIR = 'notes'
MARKS_DIR = 'marks'
BOOKMARKS_DIR = 'favs'
CONFIG_DIR = 'config'

OLD_DATA_PATH = os.path.join(HOME, '.' + APP_NAME)

DATA_PATH = GetUserDataDir()
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
BOOK_FONT = os.path.join(CONFIG_PATH, 'font_book.cfg')
DICT_FONT = os.path.join(CONFIG_PATH, 'font_dict.cfg')
SEARCH_RECT = os.path.join(CONFIG_PATH, 'rect_search.cfg')
READ_RECT = os.path.join(CONFIG_PATH, 'rect_read.cfg')

THEME_CFG = os.path.join(CONFIG_PATH, 'theme.cfg')
ACCOUNT_BASE_URL = 'https://data.etipitaka.com'
ACCOUNT_CFG = os.path.join(CONFIG_PATH, 'account.cfg')
PATCH_INDEX_URL = 'https://download.watnapahpong.org/data/etipitaka/pc/patches/patches.toml'
NOTE_STATUS_CFG = os.path.join(CONFIG_PATH, 'comment.cfg')

# Writable per-user copies of the shipped sqlite dictionaries / corpora.
# Populated lazily by the online-patcher: the shipped file is copied here
# the first time a patch is applied. All read sites use resolve_db() so
# the user copy wins when present, otherwise falls back to the shipped one.
USER_DB_DIR = os.path.join(DATA_PATH, 'databases')


def resolve_db(default_path):
    """Return the writable per-user copy of a shipped db if it exists,
    otherwise the bundled `default_path`. Used at every sqlite3.connect site
    so the online patcher can override shipped dbs without rewriting the
    bundle."""
    user_copy = os.path.join(USER_DB_DIR, os.path.basename(default_path))
    if os.path.exists(user_copy):
        return user_copy
    return default_path

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
SETTING_IMAGE = os.path.join(RESOURCES_DIR, 'setting.png')
BOOKS_IMAGE = os.path.join(RESOURCES_DIR, 'books.png')
ICON_IMAGE = os.path.join(RESOURCES_DIR, 'e-tri_64_icon.ico')
KEY_ENTER_IMAGE = os.path.join(RESOURCES_DIR, 'key_enter.png')
FILE_DELETE_IMAGE = os.path.join(RESOURCES_DIR, 'file_delete.png')

STAR_IMAGE = os.path.join(RESOURCES_DIR, 'star.png')
NOTES_IMAGE = os.path.join(RESOURCES_DIR, 'edit-notes.png')
ACCOUNT_IMAGE = os.path.join(RESOURCES_DIR, 'account.png')
DICT_IMAGE = os.path.join(RESOURCES_DIR, 'dict.png')
THAI_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'thaidict.png')
PALI_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'palidict.png')
ENGLISH_DICT_IMAGE = os.path.join(RESOURCES_DIR, 'palieng.png')
SEARCH_AND_COMPARE_IMAGE = os.path.join(RESOURCES_DIR, 'zoom_paper.png')
SEARCH_AND_COMPARE_ICON = os.path.join(RESOURCES_DIR, 'zoom_paper.ico')
DICT_ICON = os.path.join(RESOURCES_DIR, 'dict.ico')
LAYOUT_IMAGE = os.path.join(RESOURCES_DIR, 'layout.gif')
INC_IMAGE = os.path.join(RESOURCES_DIR, 'fontSizeUp.gif')
DEC_IMAGE = os.path.join(RESOURCES_DIR,'fontSizeDown.gif')
SAVE_IMAGE = os.path.join(RESOURCES_DIR, 'save.png')
PRINT_IMAGE = os.path.join(RESOURCES_DIR, 'print.png')
YELLOW_IMAGE = os.path.join(RESOURCES_DIR, 'yellow.png')
MARK2_IMAGE = os.path.join(RESOURCES_DIR, 'mark2.png')
MARK3_IMAGE = os.path.join(RESOURCES_DIR, 'mark3.png')
MARK4_IMAGE = os.path.join(RESOURCES_DIR, 'mark4.png')
MARK5_IMAGE = os.path.join(RESOURCES_DIR, 'mark5.png')
WHITE_IMAGE = os.path.join(RESOURCES_DIR, 'white.png')
CLEAR_IMAGE = os.path.join(RESOURCES_DIR, 'clear.png')
ABOUT_IMAGE = os.path.join(RESOURCES_DIR, 'about.png')
HEADER_IMAGE = os.path.join(RESOURCES_DIR, 'header.png')

OK_IMAGE = os.path.join(RESOURCES_DIR, 'ok.png')
NOT_OK_IMAGE = os.path.join(RESOURCES_DIR, 'not_ok.png')

DATA_DB = os.path.join(DATA_PATH, 'data.sqlite')
NOTE_DB = os.path.join(DATA_PATH, 'note.sqlite')
FAV_DB = os.path.join(DATA_PATH, 'fav.sqlite')

THAI_FIVE_BOOKS_DB = os.path.join(RESOURCES_DIR, 'thaibt.sqlite')
THAI_ROYAL_DB = os.path.join(RESOURCES_DIR, 'thai.sqlite')
THAI_MAHACHULA_DB = os.path.join(RESOURCES_DIR, 'thaimc.sqlite')
THAI_MAHACHULA2_DB = os.path.join(RESOURCES_DIR, 'thaimc2.sqlite')
THAI_MAHAMAKUT_DB = os.path.join(RESOURCES_DIR, 'thaimm.sqlite')
THAI_SCRIPT_DB = os.path.join(RESOURCES_DIR, 'thaict.sqlite')
ROMAN_SCRIPT_DB = os.path.join(RESOURCES_DIR, 'romanct.sqlite')
THAI_WATNA_DB = os.path.join(RESOURCES_DIR, 'thaiwn.sqlite')
THAI_POCKET_BOOK_DB = os.path.join(RESOURCES_DIR, 'thaipb.sqlite')
PALI_MAHACHULA_DB = os.path.join(RESOURCES_DIR, 'palimc.sqlite')
THAI_SUPREME_DB = os.path.join(RESOURCES_DIR, 'thaims.sqlite')
THAI_VINAYA_DB = os.path.join(RESOURCES_DIR, 'thaivn.sqlite')

PALI_SIAM_DB = os.path.join(RESOURCES_DIR, 'pali.sqlite')
PALI_SIAM_NEW_DB = os.path.join(RESOURCES_DIR, 'palinew.sqlite')

PALI_DICT_DB = os.path.join(RESOURCES_DIR, 'p2t_dict.sqlite')
THAI_DICT_DB = os.path.join(RESOURCES_DIR, 'thaidict.sqlite')
ENGLISH_DICT_DB = os.path.join(RESOURCES_DIR, 'pali-english.sqlite')

THAI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_thai')))
PALI_SPELL_CHECKER = SpellChecker(FileStorage(os.path.join(RESOURCES_DIR, 'spell_pali')))

BOOK_NAMES = pickle.load(open(os.path.join(RESOURCES_DIR, 'book_name.pkl'), 'rb'), encoding='utf-8')
BOOK_PAGES = pickle.load(open(os.path.join(RESOURCES_DIR, 'book_page.pkl'),  'rb'), encoding='latin-1')
BOOK_ITEMS = pickle.load(open(os.path.join(RESOURCES_DIR, 'book_item.pkl'),  'rb'), encoding='latin-1')
VOLUME_TABLE = pickle.load(open(os.path.join(RESOURCES_DIR, 'maps.pkl'),  'rb'), encoding='latin-1')
SCRIPT_ITEMS = json.loads(open(os.path.join(RESOURCES_DIR, 'ct_items.json'), encoding='utf-8').read())

MAP_MC_TO_SIAM = pickle.load(open(os.path.join(RESOURCES_DIR, 'mc_map.pkl'), 'rb'), encoding='latin-1')
MAP_MS_TO_SIAM = pickle.load(open(os.path.join(RESOURCES_DIR, 'ms_map.pkl'), 'rb'), encoding='latin-1')

FIVE_BOOKS_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'bt_toc.json'), encoding='utf-8').read())

ROMAN_SCRIPT_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'toc_rm.json'), encoding='utf-8').read())
THAI_SCRIPT_TOC = json.loads(open(os.path.join(RESOURCES_DIR, 'toc_th.json'), encoding='utf-8').read())

ROMAN_SCRIPT_TITLES = json.loads(open(os.path.join(RESOURCES_DIR, 'titles_rm.json'), encoding='utf-8').read())
THAI_SCRIPT_TITLES = json.loads(open(os.path.join(RESOURCES_DIR, 'titles_th.json'), encoding='utf-8').read())

ROMAN_BOOK_NAMES = open(os.path.join(RESOURCES_DIR, 'roman_names.txt'), encoding='utf-8').readlines()
ROMAN_MAPPING_TABLE = json.loads(open(os.path.join(RESOURCES_DIR, 'map_cst.json'), encoding='utf-8').read())
ROMAN_REVERSE_MAPPING_TABLE = json.loads(open(os.path.join(RESOURCES_DIR, 'map_cst_r.json'), encoding='utf-8').read())
ROMAN_PAGE_INDEX = json.loads(open(os.path.join(RESOURCES_DIR, 'roman_page_index.json'), encoding='utf-8').read())
ROMAN_ITEMS = json.loads(open(os.path.join(RESOURCES_DIR, 'roman_items.json'), encoding='utf-8').read())

FIVE_BOOKS_NAMES = [
    'ขุมทรัพย์จากพระโอษฐ์',
    'อริยสัจจากพระโอษฐ์ ๑',
    'อริยสัจจากพระโอษฐ์ ๒',
    'ปฏิจจสมุปบาทจากพระโอษฐ์',
    'พุทธประวัติจากพระโอษฐ์']

FIVE_BOOKS_PAGES = {
    1:466,
    2:817,
    3:1572,
    4:813,
    5:614,
}

SECTION_THAI_NAMES = [
    'พระวินัยปิฎก', 'พระสุตตันตปิฎก', 'พระอภิธรรมปิฎก'
]

SECTION_PALI_NAMES = [
    'วินยปิฏเก', 'สุตฺตนฺตปิฏเก', 'อภิธมฺมปิฏเก'
]

FIVE_BOOKS_SECTIONS = {
    1:[
        '',
        'หมวดที่ ๑ ว่าด้วย การทุศีล',
        'หมวดที่ ๒ ว่าด้วย การไม่สังวร',
        'หมวดที่ ๓ ว่าด้วย เกียรติและลาภสักการะ',
        'หมวดที่ ๔ ว่าด้วย การทำไปตามอำนาจกิเลส',
        'หมวดที่ ๕ ว่าด้วย การเป็นทาสตัณหา',
        'หมวดที่ ๖ ว่าด้วย การหละหลวมในธรรม',
        'หมวดที่ ๗ ว่าด้วย การลืมคำปฏิญาณ',
        'หมวดที่ ๘ ว่าด้วย พิษสงทางใจ',
        'หมวดที่ ๙ ว่าด้วย การเสียความเป็นผู้หลักผู้ใหญ่',
        'หมวดที่ ๑๐ ว่าด้วย การมีศีล',
        'หมวดที่ ๑๑ ว่าด้วย การมีสังวร',
        'หมวดที่ ๑๒ ว่าด้วย การเป็นอยู่ชอบ',
        'หมวดที่ ๑๓ ว่าด้วย การไม่ทำไปตามอำนาจกิเลส',
        'หมวดที่ ๑๔ ว่าด้วย การไม่เป็นทาสตัณหา',
        'หมวดที่ ๑๕ ว่าด้วย การไม่หละหลวมในธรรม',
        'หมวดที่ ๑๖ ว่าด้วย การไม่ลืมคำปฏิญาณ',
        'หมวดที่ ๑๗ ว่าด้วย การหมดพิษสงทางใจ',
        'หมวดที่ ๑๘ ว่าด้วย การไม่เสียความเป็นผู้หลักผู้ใหญ่',
        'หมวดที่ ๑๙ ว่าด้วย เนื้อนาบุญของโลก',
    ],
    2:[
        'ภาคนำ ว่าด้วย ข้อความที่ควรทราบก่อนเกี่ยวกับจตุราริยสัจ',
        'ภาค ๑ ว่าด้วย ทุกขอริยสัจ ความจริงอันประเสริฐคือทุกข์',
        'ภาค ๒ ว่าด้วย สมุทยอริยสัจ ความจริงอันประเสริฐคือเหตุให้เกิดทุกข์',
        'ภาค ๓ ว่าด้วย นิโรธอริยสัจ ความจริงอันประเสริฐคือความดับไม่เหลือของทุกข์',
    ],
    3:[
        '',
        '',
        '',
        '',
        'ภาค ๔ ว่าด้วย มัคคอริยสัจ ความจริงอันประเสริฐคือมรรค',
        'ภาคผนวก ว่าด้วย เรื่องนำมาผนวก เพื่อความสะดวกแก่การอ้างอิงสำหรับเรื่องที่ตรัสซ้ำ ๆ บ่อย ๆ',
    ],
    4:[
        'บทนำ ว่าด้วย เรื่องที่ควรทราบก่อนเกี่ยวกับปฏิจจสมุปบาท',
        'หมวด ๑ ว่าด้วย ลักษณะ – ความสำคัญ – วัตถุประสงค์ของเรื่องปฏิจจสมุปบาท',
        'หมวด ๒ ว่าด้วย ปฏิจจสมุปบาทคืออริยสัจสมบูรณ์แบบ',
        'หมวด ๓ ว่าด้วย บาลีแสดงว่าปฏิจจสมุปบาทไม่ใช่เรื่องข้ามภพข้ามชาติ',
        'หมวด ๔ ว่าด้วย ปฏิจจสมุปบาทเกิดได้เสมอในชีวิตประจำวันของคนเรา',
        'หมวด ๕ ว่าด้วย ปฏิจจสมุปบาทซึ่งแสดงการเกิดดับแห่งกิเลสและความทุกข์',
        'หมวด ๖ ว่าด้วย ปฏิจจสมุปบาทที่ตรัสในรูปของการปฏิบัติ',
        'หมวด ๗ ว่าด้วย โทษของการไม่รู้และอานิสงส์ของการรู้ปฏิจจสมุปบาท',
        'หมวด ๘ ว่าด้วย ปฏิจจสมุปบาทเกี่ยวกับความเป็นพระพุทธเจ้า',
        'หมวด ๙ ว่าด้วย ปฏิจจสมุปบาทกับอริยสาวก',
        'หมวด ๑๐ ว่าด้วย ปฏิจจสมุปบาทนานาแบบ',
        'หมวด ๑๑ ว่าด้วย ลัทธิหรือทิฏฐิที่ขัดกับปฏิจจสมุปบาท',
        'หมวด ๑๒ ว่าด้วย ปฏิจจสมุปบาทที่ส่อไปในทางภาษาคน - เพื่อศีลธรรม',
        'บทสรุป ว่าด้วย คุณค่าพิเศษของปฏิจจสมุปบาท',
    ],
    5:[
        'ภาคนำ ข้อความให้เกิดความสนใจในพุทธประวัติ',
        'ภาค ๑ เริ่มแต่การเกิดแห่งวงศ์สากยะ, เรื่องก่อนประสูติ, จนถึงออกผนวช',
        'ภาค ๒ เริ่มแต่ออกผนวชแล้วเที่ยวเสาะแสวงหาความรู้ ทรมานพระองค์ จนได้ตรัสรู้',
        'ภาค ๓ เริ่มแต่ตรัสรู้แล้วทรงประกอบด้วยพระคุณธรรมต่าง ๆ จนเสด็จไปโปรดปัญจวัคคีย์บรรลุผล',
        'ภาค ๔ เรื่องเบ็ดเตล็ดใหญ่น้อยต่าง ๆ ตั้งแต่โปรดปัญจวัคคีย์แล้ว  ไปจนถึงจวนจะปรินิพพาน',
        'ภาค ๕ การปรินิพพาน',
        'ภาค ๖ เรื่องการบำเพ็ญบารมีในอดีตชาติ ซึ่งเต็มไปด้วยทิฏฐานุคติอันสาวกในภายหลังพึงดำเนินตาม',
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
    9: 'palimc',
    10: 'thaims',
    11: 'thaivn',
    12: 'thaimc2'
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
    8: 'palimc',
    9: 'thaivn'
}

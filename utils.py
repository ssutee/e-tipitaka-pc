#-*- coding:utf-8 -*-

import wx
import os, codecs, json, shutil
import constants
import sqlite3
from appdirs import user_data_dir

class BookmarkManager(object):
    def __init__(self, view, code):
        self._view = view
        self._code = code
                
    def Save(self, code, note, volume, page, pid):
        conn = sqlite3.connect(constants.FAV_DB)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO %s VALUES (?,?,?,?)'%(code), (note, volume, page, pid))
        conn.commit()        
        conn.close()

        
    def MakeMenu(self, menu, evtHandler):
        conn = sqlite3.connect(constants.FAV_DB)
        cursor = conn.cursor()                    
        
        def _MakeMenu(root, pid):            
            cursor.execute('SELECT ROWID, note, volume, page, parent_id FROM %s WHERE parent_id=?'%(self._code), (pid,))
            rows =cursor.fetchall()
            for row in rows:
                rowId, note, volume, page, pid = row
                if volume == 0:
                    child = wx.Menu()
                    _MakeMenu(child, rowId)
                    root.Append(wx.ID_ANY, note, child)
                else:
                    note = 'เล่มที่ %d หน้าที่ %d : %s'%(volume, page, note)                    
                    menuItem = root.Append(wx.ID_ANY, ArabicToThai(note))
                    menuItem.volume = volume
                    menuItem.page = page
                    self._view.Bind(wx.EVT_MENU, evtHandler, menuItem)
        _MakeMenu(menu, 0)

        conn.close()
        
    @property
    def Items(self):
        return self._items

def UpdateDatabases():
    if os.path.exists(constants.DATA_DB):
        conn = sqlite3.connect(constants.DATA_DB)
        cursor = conn.cursor()
        if cursor.execute('PRAGMA user_version').fetchone()[0] < 2:
            cursor.execute('PRAGMA user_version=2')
            try:
                cursor.execute('ALTER TABLE History ADD COLUMN pages TEXT')
            except sqlite3.OperationalError as e:
                pass            
            conn.commit()                        
        if cursor.execute('PRAGMA user_version').fetchone()[0] == 2:
            cursor.execute('PRAGMA user_version=3')
            try:
                cursor.execute('CREATE TABLE IF NOT EXISTS temp_table (id INTEGER PRIMARY KEY AUTOINCREMENT, keywords text NOT NULL, total INTEGER NOT NULL, code VARCHAR(200) NOT NULL, read TEXT NOT NULL, skimmed TEXT NOT NULL, pages TEXT, notes TEXT)')
                cursor.execute('INSERT INTO temp_table SELECT * FROM History')
                cursor.execute('DROP TABLE History')
                cursor.execute('ALTER TABLE temp_table RENAME TO History')
            except sqlite3.OperationalError as e:
                pass                        
            conn.commit()            
        if cursor.execute('PRAGMA user_version').fetchone()[0] == 3:
            cursor.execute('PRAGMA user_version=4')            
            try:
                cursor.execute('ALTER TABLE History ADD COLUMN notes TEXT')
            except sqlite3.OperationalError as e:
                pass        
            conn.commit()    
        if cursor.execute('PRAGMA user_version').fetchone()[0] == 4:
            cursor.execute('PRAGMA user_version=5')
            try:
                cursor.execute('ALTER TABLE SearchAndCompareHistory ADD COLUMN count1 INTEGER')
                cursor.execute('ALTER TABLE SearchAndCompareHistory ADD COLUMN count2 INTEGER')
            except sqlite3.OperationalError as e:
                pass

        conn.close()        
        
    if os.path.exists(constants.NOTE_DB):
        conn = sqlite3.connect(constants.NOTE_DB)
        cursor = conn.cursor()
        if cursor.execute('PRAGMA user_version').fetchone()[0] < 2:
            print('update database')
            cursor.execute('CREATE TABLE IF NOT EXISTS temp_table (id INTEGER PRIMARY KEY AUTOINCREMENT, volume INTEGER NOT NULL, page INTEGER NOT NULL, code VARCHAR(200) NOT NULL, filename VARCHAR(255) NOT NULL, text TEXT NOT NULL)')
            cursor.execute('INSERT INTO temp_table SELECT * FROM Note')
            cursor.execute('DROP TABLE Note')
            cursor.execute('ALTER TABLE temp_table RENAME TO Note')
            cursor.execute('PRAGMA user_version=2')
            conn.commit()                
        conn.close()

    if not os.path.exists(constants.FAV_DB):
        conn = sqlite3.connect(constants.FAV_DB)
        cursor = conn.cursor()
        cursor.execute('PRAGMA user_version=1')
        
        for code in constants.CODES:
            cursor.execute('CREATE TABLE IF NOT EXISTS %s (note TEXT, volume INTEGER, page INTEGER, parent_id INTEGER)'%(code))
            favfile = os.path.join(constants.BOOKMARKS_PATH,'%s.fav'%(code))
            if os.path.exists(favfile):
                pids = [0]
                with codecs.open(favfile,'r','utf8') as f:
                    for text in f:
                        if text.strip() == '': continue
                        level = text.rstrip().count('\t')
                        if level > len(pids): continue
                        pid = pids[level]
                        if text.strip()[0] == '~': # folder item
                            cursor.execute('INSERT INTO %s VALUES (?,?,?,?)'%(code), (text.strip().strip('~'), 0, 0, pid))
                            try:
                                pids[level+1] = cursor.lastrowid
                            except IndexError as e:
                                pids.append(cursor.lastrowid)
                        else: # note item
                            tokens = ArabicToThai(text.strip()).split()
                            _, note = text.strip().split(':')
                            try:
                                cursor.execute('INSERT INTO %s VALUES (?,?,?,?)'%(code), (note.strip(), int(tokens[1]), int(tokens[3]), pid))
                            except UnicodeEncodeError as e:
                                continue
                            except IndexError as e:
                                continue
        conn.commit()
        conn.close()

def ConvertToPaliSearch(search, force=False):
    return search.replace('ฐ', '\\uf700').replace('ญ', '\\uf70f').replace('\\u0e4d', '\\uf711') if force or 'wxMac' not in wx.PlatformInfo else search

def ConvertToThaiSearch(search, force=False):
    return search.replace('\\uf700', 'ฐ').replace('\\uf70f', 'ญ').replace('\\uf711', '\\u0e4d') if force or 'wxMac' in wx.PlatformInfo else search

def ThaiToArabic(number):
    if isinstance(number, int):
        number = str(number)
    assert isinstance(number, str), "%r is not unicode" % (number)
    d_tha = '๐๑๒๓๔๕๖๗๘๙'
    d_arb = '0123456789'
    result = ''
    for c in number:
        if c in d_tha:
            result += d_arb[d_tha.find(c)]
        else:
            result += c
    return result

def ArabicToThai(number):
    if isinstance(number, int):
        number = str(number)        
    assert isinstance(number, str), "%r is not unicode" % (number)
    d_tha = '๐๑๒๓๔๕๖๗๘๙'
    d_arb = '0123456789'
    result = ''
    for c in number:
        if c in d_arb:
            result += d_tha[d_arb.find(c)]
        else:
            result += c
    return result

def SaveTheme(theme, prefix):
    tokens = list(os.path.split(constants.THEME_CFG))
    path = os.path.join(* tokens[:-1] + [prefix + '_' + tokens[-1]])
    with codecs.open(path, 'w', 'utf8') as f:
        f.write(str(theme))

def LoadTheme(prefix):
    tokens = list(os.path.split(constants.THEME_CFG))
    path = os.path.join(* tokens[:-1] + [prefix + '_' + tokens[-1]])    
    if os.path.exists(path):
        f = codecs.open(path, 'r', 'utf8')
        theme = int(f.read().strip())
        f.close()
        return theme    
    return 0

def LoadThemeForegroundHex(prefix):
    if LoadTheme(prefix) == 1:
        return '#5E4933'
    return '#000000'

def LoadThemeBackgroundHex(prefix):
    if LoadTheme(prefix) == 1:
        return '#F9EFD8'
    return '#FFFFFF'
    
def LoadThemeForegroundColour(prefix):
    if LoadTheme(prefix) == 1:
        return wx.Colour(0x5E,0x49,0x33,0xFF)
    return wx.BLACK

def LoadThemeBackgroundColour(prefix):
    if LoadTheme(prefix) == 1:
        return wx.Colour(0xF9,0xEF,0xD8,0xFF)
    return wx.WHITE

def SaveFont(font, path, code=None):
    t = '%s,%d,%d,%d,%d' % (font.GetFaceName(),font.GetFamily(),font.GetStyle(),font.GetWeight(),font.GetPointSize())
    path = path if code is None else path + '.' + code
    if not os.path.exists(constants.CONFIG_PATH):
        os.mkdir(constants.CONFIG_PATH)
    with codecs.open(path,'w','utf8') as f:
        f.write(t)        

def LoadFont(path, code=None):
    font = wx.Font(14 if wx.Port == '__WXGTK__' else 24, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
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

    with open(filename, 'w', encoding='utf-8') as f:
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

    with open(filename, encoding='utf-8') as f:
        try:
            rect, savedScreen = json.load(f)
            currentScreen = wx.GetDisplaySize()
            xScale, yScale = 1.0*savedScreen[0]/currentScreen[0], 1.0*savedScreen[1]/currentScreen[1]
        except ValueError as e:
            return None

    if isinstance(rect, list) and len(rect) == 4:
        reset_screen = xScale != 1 or yScale != 1 or rect[0]+25 > currentScreen[0] or rect[1]+25 > currentScreen[1] or rect[0] < 0 or rect[1] < 25
        return rect if not reset_screen else [currentScreen[0]/4, currentScreen[1]/4, currentScreen[0]/2, currentScreen[1]/2]

    return None

def LoadReadWindowPosition():
    return LoadWindowPosition(constants.READ_RECT)
    
def LoadSearchWindowPosition():
    return LoadWindowPosition(constants.SEARCH_RECT)

def LoadNoteStatus():
    if not os.path.exists(constants.NOTE_STATUS_CFG):
        return True
    return True if open(constants.NOTE_STATUS_CFG, encoding='utf-8').read().strip() == '1' else False

def SaveNoteStatus(status):
    f = open(constants.NOTE_STATUS_CFG, 'w', encoding='utf-8')
    f.write('1' if status else '0')
    f.close()

def MakeKey(code, index):
    return '%s:%d'%(code, index)
    
def SplitKey(key):
    if key is not None:
        tokens = key.split(':')
        return tokens[0], int(tokens[1])
    return None, 0

def ShortName(code):    
    if code == constants.THAI_ROYAL_CODE:
        return 'ฉบับหลวง'
    if code == constants.PALI_SIAM_CODE:
        return 'สยามรัฐ ๒๕๓๘'
    if code == constants.THAI_MAHAMAKUT_CODE:
        return 'มหามกุฏ'
    if code == constants.THAI_MAHACHULA_CODE:
        return 'มหาจุฬา (ไทย ๑)'
    if code == constants.THAI_MAHACHULA2_CODE:
        return 'มหาจุฬา (ไทย ๒)'        
    if code == constants.ROMAN_SCRIPT_CODE:
        return 'roman'
    if code == constants.THAI_FIVE_BOOKS_CODE:
        return 'จากพระโอษฐ์'
    if code == constants.THAI_WATNA_CODE:
        return 'พุทธวจนปิฎก ๓๓ เล่ม'
    if code == constants.THAI_POCKET_BOOK_CODE:
        return 'หมวดธรรม'
    if code == constants.PALI_MAHACHULA_CODE:
        return 'มหาจุฬา (บาลี)'
    if code == constants.THAI_SUPREME_CODE:
        return 'เฉลิมพระเกียรติ ๒๕๔๙'
    if code == constants.THAI_VINAYA_CODE:
        return 'อริยวินัย'
    if code == constants.PALI_SIAM_NEW_CODE:
        return 'สยามรัฐ ๒๔๗๐'
    raise ValueError(code)

def GetFilePaths(directory):
    """
    This function will generate the file names in a directory 
    tree by walking the tree either top-down or bottom-up. For each 
    directory in the tree rooted at directory top (including top itself), 
    it yields a 3-tuple (dirpath, dirnames, filenames).
    """
    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory

def MoveOldUserData():
    for filename in GetFilePaths(constants.VIRTURE_STORE):
        curdir = os.path.dirname(os.path.realpath(__file__))
        if os.path.join(constants.APP_NAME, '') in filename or os.path.join(os.path.split(curdir)[-1], '') in filename:
            os.remove(filename)

    if os.path.exists(constants.IMPORTED_MARK_FILE) or not os.path.exists(constants.OLD_DATA_PATH):
        return

    for filename in os.listdir(constants.OLD_DATA_PATH):
        full_path = os.path.join(constants.OLD_DATA_PATH, filename)
        if os.path.isfile(full_path):
            shutil.copy(full_path, constants.DATA_PATH)
        else:
            shutil.copytree(full_path, os.path.join(constants.DATA_PATH, filename))

    fout = open(constants.IMPORTED_MARK_FILE, 'w', encoding='utf-8')
    fout.close()

    UpdateDatabases()

def RemoveOldDatabases():
    import glob

    if not getattr(__builtins__, "WindowsError", None):
        class WindowsError(OSError): pass

    for dbfile in glob.glob(os.path.join(constants.RESOURCES_DIR, '*.db')):
        try:
            os.remove(dbfile)
        except WindowsError as e:
            pass

def GetUserDataDir():    
    from constants import APP_NAME, APP_AUTHOR

    data_dir = user_data_dir(APP_NAME, APP_AUTHOR)
    user_data_cfg_path = os.path.join(data_dir, 'data_path.cfg')

    if os.path.exists(user_data_cfg_path):
        with open(user_data_cfg_path, 'r', encoding='utf-8') as f:
            path = f.readline().rstrip()
            if os.path.exists(path):
                return path
    return user_data_dir(APP_NAME, APP_AUTHOR)

def SaveUserDataDir(path):
    from constants import APP_NAME, APP_AUTHOR

    data_dir = user_data_dir(APP_NAME, APP_AUTHOR)
    user_data_cfg_path = os.path.join(data_dir, 'data_path.cfg')
    with open(user_data_cfg_path, 'w', encoding='utf-8') as f:
        f.write(path)

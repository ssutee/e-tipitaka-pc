#-*- coding:utf-8 -*-

import wx
import os, codecs, json
import constants
import sqlite3

class BookmarkManager(object):
    def __init__(self, view, code):
        self._items = []
        self._view = view
        self._code = code
        self.Load()
                
    def Load(self):
        filename = os.path.join(constants.BOOKMARKS_PATH,'%s.fav'%(self._code))
        if not os.path.exists(filename): return
        self._items = []
        roots = [self._items]
        with codecs.open(filename,'r','utf8') as f:
            for text in f:
                if text.strip() == '': continue
                n_root = text.rstrip().count(u'\t')
                if n_root > len(roots): continue
                root = roots[n_root]
                if text.strip()[0] == '~':
                    child = []
                    root.append({text.strip().strip(u'~') : child})
                    try:
                        roots[n_root+1] = child
                    except IndexError,e:
                        roots.append(child)
                else:
                    tokens = ArabicToThai(text.strip()).split()
                    root.append((int(tokens[1]), int(tokens[3]), text.strip()))
        map(lambda x:x.sort(), roots)
        
    def Save(self):

        def _Save(items, out, depth=0):
            for item in items:
                if isinstance(item, dict):
                    folder = item.keys()[0]
                    out.write(u'\t'*depth + '~' + folder + '\n')
                    _Save(item[folder], out, depth+1)
                elif isinstance(item, tuple):
                    out.write(u'\t'*depth + item[2] + '\n')

        if not os.path.exists(constants.BOOKMARKS_PATH):
            os.makedirs(constants.BOOKMARKS_PATH)
        
        with codecs.open(os.path.join(constants.BOOKMARKS_PATH,'%s.fav'%(self._code)),'w','utf8') as out:
            _Save(self._items, out)

        
    def MakeMenu(self, menu, handler):        
        def _MakeMenu(root, items):
            for item in items:
                if isinstance(item, dict):
                    child = wx.Menu()
                    folder = item.keys()[0]
                    _MakeMenu(child, item[folder])
                    root.AppendMenu(-1, folder, child)
                elif isinstance(item, tuple):
                    menuItem = root.Append(-1, item[2])
                    menuItem.volume = item[0]
                    menuItem.page = item[1]
                    self._view.Bind(wx.EVT_MENU, handler, menuItem)
        _MakeMenu(menu, self._items)
        
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
            except sqlite3.OperationalError,e:
                pass
            conn.commit()
        conn.close()

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

def SaveTheme(theme, prefix):
    tokens = list(os.path.split(constants.THEME_CFG))
    path = os.path.join(* tokens[:-1] + [prefix + '_' + tokens[-1]])
    with codecs.open(path, 'w', 'utf8') as f:
        f.write(unicode(theme))

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
    return True if open(constants.NOTE_STATUS_CFG).read().strip() == '1' else False

def SaveNoteStatus(status):
    f = open(constants.NOTE_STATUS_CFG, 'w')
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
        return u'ฉบับหลวง'
    if code == constants.PALI_SIAM_CODE:
        return u'สยามรัฐ'
    if code == constants.THAI_MAHAMAKUT_CODE:
        return u'มหามกุฏ'
    if code == constants.THAI_MAHACHULA_CODE:
        return u'มหาจุฬา'
    if code == constants.ROMAN_SCRIPT_CODE:
        return u'roman'
    if code == constants.THAI_FIVE_BOOKS_CODE:
        return u'จากพระโอษฐ์'
    if code == constants.THAI_WATNA_CODE:
        return u'พุทธวจนปิฎก'
    if code == constants.THAI_POCKET_BOOK_CODE:
        return u'หมวดธรรม'
    raise ValueError(code)

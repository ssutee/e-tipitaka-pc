#-*- coding:utf-8 -*-

import wx
import sqlite3, cPickle, re
import constants, utils

import i18n
_ = i18n.language.ugettext

from pony.orm import Database, Required, Optional, db_session, select, desc, LongUnicode

db = Database('sqlite', constants.NOTE_DB, create_db=True)

class Note(db.Entity):
    volume = Required(int)
    page = Required(int)
    code = Required(unicode)
    filename = Optional(unicode)
    text = Optional(unicode)

db.generate_mapping(create_tables=True)

class Engine(object):
    
    def __init__(self):
        self._searcher = None
        self._conn = None
        self._cache = {}
        
    def __del__(self):
        if self._conn is not None:
            self._conn.close()

    @property
    def HasPdf(self):
        return False
        
    def Query(self, volume, page):
        results = self._cache.get('q:%d:%d'%(volume, page), self._searcher.execute(*self.PrepareStatement(volume, page)))
        if 'q:%d:%d'%(volume, page) not in self._cache: self._cache['q:%d:%d'%(volume, page)] = results
        return self.ProcessResult(results.fetchone())
        
    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM %s WHERE volumn = ? AND page = ?'%(self._code)
        args = ('%02d'%(volume), '%04d'%(page))
        return select, args
    
    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[0]
            r['page'] = result[1]
            r['items'] = result[2]
            r['content'] = result[3]
        return r
    
    def GetTotalPages(self, volume):
        return int(constants.BOOK_PAGES.get('%s_%d' % (self._code, volume), 0))
        
    def GetFirstPageNumber(self, volume):
        return 0
        
    def GetSubItemsInVolume(self, volume):
        return constants.BOOK_ITEMS[self._code.encode('utf8','ignore')][volume].keys()
        
    def GetItemsInVolume(self, volume, sub):
        return constants.BOOK_ITEMS[self._code.encode('utf8','ignore')][volume][sub].keys()
        
    def GetFirstPage(self, volume):
        pages = map(lambda x:u'%s'%(x), range(0, self.GetTotalPages(volume)))
        

        if len(pages) == 0:
            return u''

        text1 = u'\nพระไตรปิฎกเล่มที่ %d มี\n\tตั้งแต่หน้าที่ %d - %d'%(volume, int(pages[0])+1, int(pages[-1]))
        text2 = u''

        sub = self.GetSubItemsInVolume(volume)
        if len(sub) == 1:
            items = self.GetItemsInVolume(volume, 1)
            text2 = u'\n\tตั้งแต่ข้อที่ %s - %s'%(items[0],items[-1])
        else:
            text2 = u'\n\tแบ่งเป็น %d เล่มย่อย มีข้อดังนี้'%(len(sub))
            for s in sub:
                items = self.GetItemsInVolume(volume, s)
                items.sort()
                text2 = text2 + '\n\t\t %d) %s.%d - %s.%d'%(s, items[0], s, items[-1], s)

        return utils.ArabicToThai(text1 + text2)
        
    def GetContent(self, result):
        return result.get('content')
        
    def GetFormatter(self, volume, page):
        result = self.Query(volume, page)
        content = self.GetContent(result)
        
        formatter = result.get('display', '')
                    
        header = result.get('header')
        if header is not None and len(header) > 0:
            formatter += u' h1|0|%d'%(len(header))
            
        footer = result.get('footer')
        if footer is not None and len(footer) > 0:
            formatter += u' s3|%d|%d'%(len(content)-len(footer), len(content)+1)

        return formatter
        
    def GetItems(self, volume, page):
        result = self.Query(volume, page)
        return map(int, result['items'].split()) if len(result) > 0 else []
        
    def GetSection(self, volume, page):
        return self.Query(volume, page).get('section', 0)

    def GetPage(self, volume, page):
        return self.GetContent(self.Query(volume, page)) if page > 0 else self.GetFirstPage(volume)
        
    def GetTitle(self, volume):
        raise NotImplementedError('Subclass needs to implement this method!')

    def GetSectionName(self, volume):
        raise NotImplementedError('Subclass needs to implement this method!')

    def GetSubtitle(self, volume, section=None):
        tokens = constants.BOOK_NAMES['%s_%s' % (self._code, str(volume))].decode('utf8','ignore').split()
        return '%s %s'%(' '.join(tokens[:3]),' '.join(tokens[3:]))

    def GetSectionBoundary(self, position):
        if position == 0:
            return 8
        if position == 1:
            return 33
        return 45

    def GetBookName(self, volume):
        return constants.BOOK_NAMES['%s_%s' % (self._code, str(volume))].decode('utf8','ignore')

    def GetBookListItems(self):
        return ['%2s. %s' % (utils.ArabicToThai(volume+1), self.GetBookName(volume+1)) for volume in range(self.GetSectionBoundary(2))]
        
    def GetCompareChoices(self):
        return constants.COMPARE_CHOICES
        
    def GetSubItem(self, volume, page, item): 
        for sub in constants.BOOK_ITEMS[self._code][volume]:
            if item in constants.BOOK_ITEMS[self._code][volume][sub]:
                pages = constants.BOOK_ITEMS[self._code][volume][sub][item]
                if page in pages:
                    return item, sub
        return item, 1
        
    @property
    def HighlightOffset(self):
        return 0
        
    def ConvertSpecialCharacters(self, text):
        return text

    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:
            return constants.BOOK_ITEMS[self._code][volume][sub][item][0]
        except KeyError, e:
            return 0
        except TypeError, e:
            return 0

    def ConvertVolume(self, volume, item, sub):
        return volume
        
    def GetComparingVolume(self, volume, page):
        return volume
    
    def ConvertToPivot(self, volume, page, item):
        item, sub = self.GetSubItem(volume, page, item)        
        return self.GetComparingVolume(volume, page), item, sub

    def ConvertFromPivot(self, volume, item, sub):
        volume = self.ConvertVolume(volume, item, sub)
        page = self.ConvertItemToPage(volume, item, sub, True)
        return volume, page

    def CanSelectComparingItem(self):
        return True

class ThaiRoyalEngine(Engine):
    
    def __init__(self):
        super(ThaiRoyalEngine, self).__init__()
        self._code = constants.THAI_ROYAL_CODE
        self._conn = sqlite3.connect(constants.THAI_ROYAL_DB)
        self._searcher = self._conn.cursor()
                
    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = ('%02d'%(volume), '%04d'%(page))
        return select, args


    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับหลวง (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับหลวง (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))
        
    def GetSectionName(self, volume):
        if volume <= 8:
            return constants.SECTION_THAI_NAMES[0]
        if volume <= 33:
            return constants.SECTION_THAI_NAMES[1]
        return constants.SECTION_THAI_NAMES[2]        
        
class PaliSiamEngine(Engine):

    def __init__(self):
        super(PaliSiamEngine, self).__init__()
        self._code = constants.PALI_SIAM_CODE
        self._conn = sqlite3.connect(constants.PALI_SIAM_DB)
        self._searcher = self._conn.cursor()

    @property
    def HasPdf(self):
        return True        

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = ('%02d'%(volume), '%04d'%(page))
        return select, args
        
    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
        return r
        
    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับสยามรัฐ (ภาษาบาลี)'
        return u'พระไตรปิฎก ฉบับสยามรัฐ (ภาษาบาลี) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))
        
    def GetPage(self, volume, page):
        return super(PaliSiamEngine, self).GetPage(volume, page).replace(u'ฐ',u'\uf700').replace(u'ญ',u'\uf70f').replace(u'\u0e4d',u'\uf711')

    def GetSectionName(self, volume):
        if volume <= 8:
            return constants.SECTION_PALI_NAMES[0]
        if volume <= 33:
            return constants.SECTION_PALI_NAMES[1]
        return constants.SECTION_PALI_NAMES[2]        
        
    def ConvertSpecialCharacters(self, text):
        return utils.ConvertToPaliSearch(text, True)        

class ThaiVinayaEngine(Engine):

    def __init__(self):
        super(ThaiVinayaEngine, self).__init__()
        self._code = constants.THAI_VINAYA_CODE
        self._conn = sqlite3.connect(constants.THAI_VINAYA_DB)
        self._searcher = self._conn.cursor()

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = (volume, page)
        return select, args

    def GetContent(self, result):
        return result.get('content')

    def GetTitle(self, volume=None):
        return u'อริยวินัย'

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['content'] = result[3]
            r['buddhawaj'] = result[4]
            r['display'] = result[5]
        return r

    def GetCompareChoices(self):
        return constants.COMPARE_CHOICES

    def ConvertVolume(self, volume, item, sub):
        return volume

    def GetComparingVolume(self, volume, page):
        return 9 if volume == 1 else volume+1

    def GetItems(self, volume, page):
        self._searcher.execute('SELECT content FROM main WHERE volume=? AND page=?', (int(volume), int(page)))
        result = self._searcher.fetchone()
        return [] if volume > 9 else map(int, map(utils.ThaiToArabic, re.findall(ur'\[([๐-๙]+)\]', result[0])))

    def GetSubtitle(self, volume, section=None):
        tokens = constants.BOOK_NAMES['%s_%s' % (self._code, str(volume))].decode('utf8','ignore').split()
        return '%s'%(' '.join(tokens[1:]))

        
    def GetSubItem(self, volume, page, item):
        return item, 1

    def GetSectionBoundary(self, position):
        return 11

    def GetFirstPageNumber(self, volume):
        return 1

    def GetTotalPages(self, volume):
        self._searcher.execute('SELECT COUNT(_id) FROM main WHERE volume=?', (int(volume),))
        result = self._searcher.fetchone()
        return result[0] if result is not None else 0

    def CanSelectComparingItem(self):
        return True


class ThaiPocketBookEngine(Engine):

    def __init__(self):
        super(ThaiPocketBookEngine, self).__init__()
        self._code = constants.THAI_POCKET_BOOK_CODE
        self._conn = sqlite3.connect(constants.THAI_POCKET_BOOK_DB)
        self._searcher = self._conn.cursor()

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = (volume, page)
        return select, args

    def GetContent(self, result):
        return result.get('content')

    def GetTitle(self, volume=None):
        return u'%s เล่มที่ %s' % (_('Thai Pocket Book'), utils.ArabicToThai(unicode(volume)))

    def GetSubtitle(self, volume, section=None):
        return constants.BOOK_NAMES['%s_%s' % ('thaipb', str(volume))].decode('utf8','ignore') if volume else _('Thai Pocket Book')

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['content'] = result[3]
            r['buddhawaj'] = result[4]
            r['display'] = result[5]
        return r

    def GetCompareChoices(self):
        return []

    def GetItems(self, volume, page):
        return []
        
    def GetSubItem(self, volume, page, item):
        return item, 1

    def GetSectionBoundary(self, position):
        return 16

    def GetFirstPageNumber(self, volume):
        return 1

    def GetTotalPages(self, volume):
        self._searcher.execute('SELECT COUNT(_id) FROM main WHERE volume=?', (int(volume),))
        result = self._searcher.fetchone()
        return result[0] if result is not None else 0

    def CanSelectComparingItem(self):
        return False

class ThaiWatnaEngine(Engine):

    def __init__(self):
        super(ThaiWatnaEngine, self).__init__()
        self._code = constants.THAI_WATNA_CODE
        self._conn = sqlite3.connect(constants.THAI_WATNA_DB)
        self._searcher = self._conn.cursor()

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = (volume, page)
        return select, args

    def GetContent(self, result):
        return result.get('content')

    def GetTitle(self, volume=None):
        return u'พุทธวจนปิฎก เล่มที่ %s'%(utils.ArabicToThai(unicode(volume))) if volume else _('Buddhawajana Pitaka')

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
            r['buddhawaj'] = result[5]
            r['display'] = result[6]
        return r

    def GetSectionName(self, volume):
        if volume <= 25:
            return constants.SECTION_THAI_NAMES[0]
        return constants.SECTION_THAI_NAMES[1]
            
    def GetSectionBoundary(self, position):
        if position == 0:
            return 25
        return 33

    def GetComparingVolume(self, volume, page):
        if volume <= 25:
            return volume + 8
        return volume - 25

    def ConvertVolume(self, volume, item, sub):
        if volume <= 8:
            return volume + 25
        return volume - 8

class PaliMahaChulaEngine(Engine):

    def __init__(self):
        super(PaliMahaChulaEngine, self).__init__()
        self._code = constants.PALI_MAHACHULA_CODE
        self._conn = sqlite3.connect(constants.PALI_MAHACHULA_DB)
        self._searcher = self._conn.cursor()

    @property
    def HighlightOffset(self):
        return 1 if 'wxMac' in wx.PlatformInfo else 0

    def GetBookName(self, volume):
        return constants.BOOK_NAMES['%s_%s' % ('pali', str(volume))].decode('utf8','ignore')

    def GetSubtitle(self, volume, section=None):
        tokens = constants.BOOK_NAMES['%s_%s' % ('pali', str(volume))].decode('utf8','ignore').split()
        return '%s %s'%(' '.join(tokens[:3]),' '.join(tokens[3:]))

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?' 
        args = (volume, page)
        return select, args

    def GetContent(self, result):
        return None if result.get('content') is None else result.get('content') + result.get('footer', u'')

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาบาลี)'
        return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาบาลี) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
            r['footer'] = result[5]
            r['display'] = result[6]
        return r

    def GetSubItem(self, volume, page, item): 
        item, sub = super(PaliMahaChulaEngine, self).GetSubItem(volume, page, item)
        page = constants.BOOK_ITEMS['thaimc'][volume][sub][item][0]
        return map(int, constants.MAP_MC_TO_SIAM['v%d-p%d'%(volume, page)])

    def GetSectionName(self, volume):
        if volume <= 8:
            return constants.SECTION_PALI_NAMES[0]
        if volume <= 33:
            return constants.SECTION_PALI_NAMES[1]
        return constants.SECTION_PALI_NAMES[2]        
        
    def ConvertSpecialCharacters(self, text):
        return utils.ConvertToPaliSearch(text, True)        

    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:
            return int(constants.MAP_MC_TO_SIAM['v%d-%d-i%d'%(volume, sub, item)]) if checked else constants.BOOK_ITEMS[self._code][volume][sub][item][0]
        except KeyError, e:
            return 0
        except TypeError, e:
            return 0

    def CanSelectComparingItem(self):
        return False

    def GetTotalPages(self, volume):
        self._searcher.execute('SELECT COUNT(_id) FROM main WHERE volume=?', (int(volume),))
        result = self._searcher.fetchone()
        return result[0] if result is not None else 0        

class ThaiSupremeEngine(Engine):
    def __init__(self):
        super(ThaiSupremeEngine, self).__init__()
        self._code = constants.THAI_SUPREME_CODE
        self._conn = sqlite3.connect(constants.THAI_SUPREME_DB)
        self._searcher = self._conn.cursor()

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = (volume, page)
        return select, args

    def GetContent(self, result):
        return None if result.get('content') is None else result.get('content') + '\n' + result.get('footer', u'')

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหาเถรฯ (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับมหาเถรฯ (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))
    
    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
            r['display'] = result[5]            
            r['footer'] = result[7]
        return r

    def GetSubItem(self, volume, page, item):
        return map(int, constants.MAP_MS_TO_SIAM['v%d-p%d'%(volume, page)])

    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:
            return int(constants.MAP_MS_TO_SIAM['v%d-%d-i%d'%(volume, sub, item)]) if checked else constants.BOOK_ITEMS[self._code][volume][sub][item][0]
        except KeyError, e:
            return 0
        except TypeError, e:
            return 0

    def CanSelectComparingItem(self):
        return False

    @property
    def HighlightOffset(self):
        return 1 if 'wxMac' in wx.PlatformInfo else 0


class ThaiMahaChulaEngine(Engine):

    def __init__(self):
        super(ThaiMahaChulaEngine, self).__init__()
        self._code = constants.THAI_MAHACHULA_CODE
        self._conn = sqlite3.connect(constants.THAI_MAHACHULA_DB)
        self._searcher = self._conn.cursor()

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = ('%02d'%(volume), '%04d'%(page))
        return select, args

    def GetContent(self, result):
        return None if result.get('content') is None else result.get('header', u'') + result.get('content') + result.get('footer', u'')

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['header'] = result[4]
            r['footer'] = result[5]
            r['display'] = result[6]
            r['content'] = result[7]
        return r
        
    def GetSubItem(self, volume, page, item):
        return map(int, constants.MAP_MC_TO_SIAM['v%d-p%d'%(volume, page)])
        
    @property
    def HighlightOffset(self):
        return 1 if 'wxMac' in wx.PlatformInfo else 0

    def GetSectionName(self, volume):
        if volume <= 8:
            return constants.SECTION_THAI_NAMES[0]
        if volume <= 33:
            return constants.SECTION_THAI_NAMES[1]
        return constants.SECTION_THAI_NAMES[2]        

    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:
            return int(constants.MAP_MC_TO_SIAM['v%d-%d-i%d'%(volume, sub, item)]) if checked else constants.BOOK_ITEMS[self._code][volume][sub][item][0]
        except KeyError, e:
            return 0
        except TypeError, e:
            return 0

    def CanSelectComparingItem(self):
        return False


class ThaiMahaMakutEngine(Engine):

    def __init__(self):
        super(ThaiMahaMakutEngine, self).__init__()
        self._code = constants.THAI_MAHAMAKUT_CODE
        self._conn = sqlite3.connect(constants.THAI_MAHAMAKUT_DB)
        self._searcher = self._conn.cursor()

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหามกุฏฯ (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับมหามกุฏฯ (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume = ? AND page = ?'
        args = ('%02d'%(volume), '%04d'%(page))
        return select, args

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[0]
            r['volume_orig'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
        return r        

    def GetSectionBoundary(self, position):
        if position == 0:
            return 10
        if position == 1:
            return 74
        return 91
        
    def GetSubItem(self, volume, page, item):    
        result = self.Query(volume, page)
        volume = int(result['volume_orig'].split()[0])
        for sub in constants.BOOK_ITEMS[self._code+'_orig'][volume]:
            if item in constants.BOOK_ITEMS[self._code+'_orig'][volume][sub]:
                pages = constants.BOOK_ITEMS[self._code+'_orig'][volume][sub][item]
                if page in pages:
                    return item, sub
        return item, 1
        
    def GetComparingVolume(self, volume, page):
        result = self.Query(volume, page)
        return int(result['volume_orig'].split()[0])

    def ConvertVolume(self, volume, item, sub):
        item = 1 if '%d-%d-%d'%(volume, sub, item) not in constants.VOLUME_TABLE[self._code] else item
        return int(constants.VOLUME_TABLE[self._code]['%d-%d-%d'%(volume, sub, item)])

    def GetSectionName(self, volume):
        if volume <= 10:
            return constants.SECTION_THAI_NAMES[0]
        if volume <= 74:
            return constants.SECTION_THAI_NAMES[1]
        return constants.SECTION_THAI_NAMES[2]        

class ThaiFiveBooksEngine(Engine):

    def __init__(self):
        super(ThaiFiveBooksEngine, self).__init__()
        self._code = constants.THAI_FIVE_BOOKS_CODE
        self._conn = sqlite3.connect(constants.THAI_FIVE_BOOKS_DB)
        self._searcher = self._conn.cursor()

    def GetFirstPageNumber(self, volume):
        return 1 if volume != 3 else 819

    def GetCompareChoices(self):
        return []

    def GetTitle(self, volume=None):
        if not volume:
            return u'ชุดห้าเล่มจากพระโอษฐ์'
        return constants.FIVE_BOOKS_NAMES[volume-1]

    def GetSubtitle(self, volume, section=None):
        return constants.FIVE_BOOKS_SECTIONS[volume][section] if section != None else ''

    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM speech WHERE book=? AND page=?'
        args = (volume, page)
        return select, args

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['content'] = result[3]
            r['section'] = int(result[2].split()[1].split('.')[1]) if len(result[2].split()[1].split('.')) > 1 else 0
        return r
        
    def GetTotalPages(self, volume):
        return constants.FIVE_BOOKS_PAGES[volume]
        
    def GetPage(self, volume, page):
        if page == 0:
            return self.GetPage(volume, 1)
        return super(ThaiFiveBooksEngine, self).GetPage(volume, page)    

    def GetItems(self, volume, page):
        return []
        
    def GetSubItem(self, volume, page, item):
        return item, 1


class ScriptEngine(Engine):
            
    def PrepareStatement(self, volume, page):
        select = 'SELECT * FROM main WHERE volume=? AND page=?'
        args = (int(volume), int(page))
        return select, args        

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
        return r
        
    def GetCompareChoices(self):
        return []
        
    def GetTotalPages(self, volume):
        self._searcher.execute('SELECT COUNT(_id) FROM main WHERE volume=?', (int(volume),))
        result = self._searcher.fetchone()
        return result[0] if result is not None else 0
        
    def GetSubItemsInVolume(self, volume):
        results = []
        for item in constants.SCRIPT_ITEMS[str(volume)]:
            for sub in constants.SCRIPT_ITEMS[str(volume)][str(item)]:
                if int(sub) not in results:
                    results.append(int(sub))
        results.sort()        
        return results

    def GetItemsInVolume(self, volume, sub):
        results = []
        for item in constants.SCRIPT_ITEMS[str(volume)]:
            if str(sub) in constants.SCRIPT_ITEMS[str(volume)][str(item)].keys():
                results.append(int(item))
        results.sort()
        return results    
        
    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:
            return constants.SCRIPT_ITEMS[str(volume)][str(item)][str(sub)]
        except KeyError, e:
            return 0
        except TypeError, e:
            return 0

    def CanSelectComparingItem(self):
        return False


class RomanScriptEngine(ScriptEngine):
    def __init__(self):
        super(RomanScriptEngine, self).__init__()
        self._code = constants.ROMAN_SCRIPT_CODE
        self._conn = sqlite3.connect(constants.ROMAN_SCRIPT_DB)
        self._searcher = self._conn.cursor()    

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[1]
            r['page'] = result[2]
            r['items'] = result[3]
            r['content'] = result[4]
        return r        

    def GetCompareChoices(self):
        return constants.COMPARE_CHOICES

    def GetTotalPages(self, volume):
        self._searcher.execute('SELECT COUNT(_id) FROM main WHERE volume=?', (int(volume),))
        result = self._searcher.fetchone()
        return result[0] if result is not None else 0        

    def GetTitle(self, volume=None):
        if volume is None:
            return 'Tipitaka (Roman Script)'
        return constants.ROMAN_SCRIPT_TITLES[str(volume)][0]

    def GetSubtitle(self, volume, section=None):
        return constants.ROMAN_SCRIPT_TITLES[str(volume)][1]

    def GetBookName(self, volume):
        return constants.ROMAN_BOOK_NAMES[volume-1].decode('utf8','ignore')

    def GetBookListItems(self):
        return ['%2s. %s' % (volume+1, self.GetBookName(volume+1)) for volume in range(self.GetSectionBoundary(2))]

    def GetSectionBoundary(self, position):
        if position == 0:
            return 5
        if position == 1:
            return 48
        return 61

    def ConvertToPivot(self, volume, page, item):
        table = constants.ROMAN_MAPPING_TABLE
        
        if str(volume) not in table or str(page) not in table[str(volume)]:
            return 0, 0, 0
        
        results = table[str(volume)][str(page)]

        if len(results) == 0:
            return 0, 0, 0

        return results[0][0], results[0][1], results[0][2]
        
    def ConvertFromPivot(self, volume, item, sub):
        table = constants.ROMAN_REVERSE_MAPPING_TABLE

        if str(volume) not in table or str(item) not in table[str(volume)] or str(sub) not in table[str(volume)][str(item)]:
            return 0, 0

        result = table[str(volume)][str(item)][str(sub)]

        return result[0], result[1]

class ThaiScriptEngine(ScriptEngine):

    def __init__(self):
        super(ThaiScriptEngine, self).__init__()
        self._code = constants.THAI_SCRIPT_CODE
        self._conn = sqlite3.connect(constants.THAI_SCRIPT_DB)
        self._searcher = self._conn.cursor()
        
    def GetTitle(self, volume=None):
        if volume is None:
            return 'Tipitaka (Thai Script)'
        return constants.THAI_SCRIPT_TITLES[str(volume)][0]

    def GetSubtitle(self, volume, section=None):
        return constants.THAI_SCRIPT_TITLES[str(volume)][1]
    
class Model(object):
    
    @staticmethod
    def Note(volume, page, code, text=None, filename=None):
        note = Note.get(volume=volume, page=page, code=code)
        if note is None: note = Note(volume=volume, page=page, code=code)
        if text is not None: note.text = text
        if filename is not None: note.filename = filename        
        return note

    @staticmethod
    def GetNoteListItems(code, text=u'', creation=False):
        
        def trim(text):
            return text if len(text) < 25 else text[:25] + u'...'
        
        return [utils.ArabicToThai(u'%s เล่มที่ %2s ข้อที่ %2s : %s' % (utils.ShortName(note.code) if code is None else u'', note.volume, note.page, trim(note.text))) for note in Model.GetNotes(code, text, creation)]
        
    @staticmethod
    def GetNotes(code, text=u'', creation=False):
        if code is None and creation:
            return select(note for note in Note if text in note.text).order_by(desc(Note.id))
        elif code is None:
            return select(note for note in Note if text in note.text).order_by(Note.volume, Note.page)
        elif creation:
            return select(note for note in Note if note.code == code and text in note.text).order_by(desc(Note.id))
        else:
            return select(note for note in Note if note.code == code and text in note.text).order_by(Note.volume, Note.page)

    @property
    def Code(self):
        return self._code

    @property
    def HasPdf(self):
        return self._engine[self._code].HasPdf
        
    @Code.setter
    def Code(self, code):
        code = code.split(":")[0]
        self._code = code
        if constants.THAI_ROYAL_CODE == code:
            self._engine[code] = ThaiRoyalEngine()
        elif constants.PALI_SIAM_CODE == code:
            self._engine[code] = PaliSiamEngine()
        elif constants.THAI_MAHACHULA_CODE == code:
            self._engine[code] = ThaiMahaChulaEngine()
        elif constants.THAI_MAHAMAKUT_CODE == code:
            self._engine[code] = ThaiMahaMakutEngine()
        elif constants.THAI_FIVE_BOOKS_CODE == code:
            self._engine[code] = ThaiFiveBooksEngine()
        elif constants.ROMAN_SCRIPT_CODE == code:
            self._engine[code] = RomanScriptEngine()
        elif constants.THAI_SCRIPT_CODE == code:
            self._engine[code] = ThaiScriptEngine()
        elif constants.THAI_WATNA_CODE == code:
            self._engine[code] = ThaiWatnaEngine()
        elif constants.THAI_POCKET_BOOK_CODE == code:
            self._engine[code] = ThaiPocketBookEngine()
        elif constants.PALI_MAHACHULA_CODE == code:
            self._engine[code] = PaliMahaChulaEngine()    
        elif constants.THAI_SUPREME_CODE == code:
            self._engine[code] = ThaiSupremeEngine()        
        elif constants.THAI_VINAYA_CODE == code:
            self._engine[code] = ThaiVinayaEngine()
        else:
            raise ValueError(code)

    def GetTitle(self, volume=None):
        return self._engine[self._code].GetTitle(volume)

    def GetTitles(self, volume, section=None):
        return self._engine[self._code].GetTitle(volume), self._engine[self._code].GetSubtitle(volume, section)

    def GetPage(self, volume, page):
        return self._engine[self._code].GetPage(volume, page)
        
    def GetFormatter(self, volume, page):        
        return self._engine[self._code].GetFormatter(volume, page)
        
    def GetItems(self, volume, page):
        return self._engine[self._code].GetItems(volume, page)

    def GetSection(self, volume, page):
        return self._engine[self._code].GetSection(volume, page)
        
    def GetSubItem(self, volume, page, item):
        return self._engine[self._code].GetSubItem(volume, page, item)

    def GetTotalPages(self, volume):
        return self._engine[self._code].GetTotalPages(volume)

    def GetFirstPageNumber(self, volume):
        return self._engine[self._code].GetFirstPageNumber(volume)

    def GetBookListItems(self):
        return self._engine[self._code].GetBookListItems()
        
    def GetCompareChoices(self):
        return self._engine[self._code].GetCompareChoices()
        
    def GetComparingVolume(self, volume, page):
        return self._engine[self._code].GetComparingVolume(volume, page)

    def ConvertItemToPage(self, volume, item, sub, checked=False):
        return self._engine[self._code].ConvertItemToPage(volume, item, sub, checked)
        
    def ConvertVolume(self, volume, item, sub):
        return self._engine[self._code].ConvertVolume(volume, item, sub)
        
    def ConvertSpecialCharacters(self, text):
        return self._engine[self._code].ConvertSpecialCharacters(text)

    def ConvertToPivot(self, volume, page, item):
        return self._engine[self._code].ConvertToPivot(volume, page, item)

    def ConvertFromPivot(self, volume, item, sub):
        return self._engine[self._code].ConvertFromPivot(volume, item, sub)

    def CanSelectComparingItem(self):
        return self._engine[self._code].CanSelectComparingItem()
        
    @property
    def HighlightOffset(self):
        return self._engine[self._code].HighlightOffset

    def __init__(self, code):
        self._engine = {}
        self.Code = code

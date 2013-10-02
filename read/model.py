#-*- coding:utf-8 -*-

import sqlite3, cPickle
import constants, utils

class Engine(object):
    
    def __init__(self):
        self._searcher = None
        
    def Query(self, volume, page):
        results = self._searcher.execute(*self.PrepareStatement(volume, page))
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
        return int(constants.BOOK_PAGES['%s_%d' % (self._code, volume)])
        
    def GetFirstPageNumber(self, volume):
        return 0
        
    def GetFirstPage(self, volume):
        pages = map(lambda x:u'%s'%(x), range(1, self.GetTotalPages(volume)))
        text1 = u'\nพระไตรปิฎกเล่มที่ %d มี\n\tตั้งแต่หน้าที่ %d - %d'%(volume, int(pages[0]), int(pages[-1])+1)
        text2 = u''

        sub = constants.BOOK_ITEMS[self._code.encode('utf8','ignore')][volume].keys()
        if len(sub) == 1:
            items = constants.BOOK_ITEMS[self._code.encode('utf8','ignore')][volume][1].keys()
            text2 = u'\n\tตั้งแต่ข้อที่ %s - %s'%(items[0],items[-1])
        else:
            text2 = u'\n\tแบ่งเป็น %d เล่มย่อย มีข้อดังนี้'%(len(sub))
            for s in sub:
                items = constants.BOOK_ITEMS[self._code.encode('utf8','ignore')][volume][s].keys()
                text2 = text2 + '\n\t\t %d) %s.%d - %s.%d'%(s,items[0],s,items[-1],s)        

        return utils.ArabicToThai(text1 + text2)
        
    def GetContent(self, result):
        return result.get('content')
        
    def GetItems(self, volume, page):
        result = self.Query(volume, page)
        return map(int, result['items'].split()) if len(result) > 0 else []
        
    def GetSection(self, volume, page):
        return self.Query(volume, page).get('section', 0)

    def GetPage(self, volume, page):
        return self.GetContent(self.Query(volume, page)) if page > 0 else self.GetFirstPage(volume)
        
    def GetTitle(self, volume):
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
        return ['%s. %s' % (utils.ArabicToThai(volume+1), self.GetBookName(volume+1)) for volume in range(self.GetSectionBoundary(2))]
        
    def GetCompareChoices(self):
        return [u'ไทย  (บาลีสยามรัฐ)', u'บาลี  (บาลีสยามรัฐ)', u'ไทย (มหามกุฏฯ)', u'ไทย (มหาจุฬาฯ)']
        
    def GetSubItem(self, volume, page, item): 
        for sub in constants.BOOK_ITEMS[self._code][volume]:
            if item in constants.BOOK_ITEMS[self._code][volume][sub]:
                pages = constants.BOOK_ITEMS[self._code][volume][sub][item]
                if page in pages:
                    return sub
        return 1
        
    def ConvertVolume(self, volume, item, sub):
        return volume

class ThaiRoyalEngine(Engine):
    
    def __init__(self):
        super(ThaiRoyalEngine, self).__init__()
        self._code = constants.THAI_ROYAL_CODE
        conn = sqlite3.connect(constants.THAI_ROYAL_DB)
        self._searcher = conn.cursor()
        
    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับหลวง (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับหลวง (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))
        
class PaliSiamEngine(Engine):

    def __init__(self):
        super(PaliSiamEngine, self).__init__()
        self._code = constants.PALI_SIAM_CODE
        conn = sqlite3.connect(constants.PALI_SIAM_DB)
        self._searcher = conn.cursor()

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับสยามรัฐ (ภาษาบาลี)'
        return u'พระไตรปิฎก ฉบับสยามรัฐ (ภาษาบาลี) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

class ThaiMahaChulaEngine(Engine):

    def __init__(self):
        super(ThaiMahaChulaEngine, self).__init__()
        self._code = constants.THAI_MAHACHULA_CODE
        conn = sqlite3.connect(constants.THAI_MAHACHULA_DB)
        self._searcher = conn.cursor()

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับมหาจุฬาฯ (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

    def ProcessResult(self, result):
        r = {}
        if result is not None:
            r['volume'] = result[0]
            r['page'] = result[1]
            r['items'] = result[2]
            r['header'] = result[3]
            r['footer'] = result[4]
            r['display'] = result[5]
            r['content'] = result[6]
        return r
        
    def GetSubItem(self, volume, page, item):
        return map(int, constants.MAP_MC_TO_SIAM['v%d-p%d'%(volume, page)])[1]

class ThaiMahaMakutEngine(Engine):

    def __init__(self):
        super(ThaiMahaMakutEngine, self).__init__()
        self._code = constants.THAI_MAHAMAKUT_CODE
        conn = sqlite3.connect(constants.THAI_MAHAMAKUT_DB)
        self._searcher = conn.cursor()

    def GetTitle(self, volume=None):
        if not volume:
            return u'พระไตรปิฎก ฉบับมหามกุฏฯ (ภาษาไทย)'
        return u'พระไตรปิฎก ฉบับมหามกุฏฯ (ภาษาไทย) เล่มที่ %s'%(utils.ArabicToThai(unicode(volume)))

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
        volume = int(result['volume_orig'])
        for sub in constants.BOOK_ITEMS[self._code+'_orig'][volume]:
            if item in constants.BOOK_ITEMS[self._code+'_orig'][volume][sub]:
                pages = constants.BOOK_ITEMS[self._code+'_orig'][volume][sub][item]
                if page in pages:
                    return sub
        return 1

    def ConvertVolume(self, volume, item, sub):
        item = 1 if '%d-%d-%d'%(volume, sub, item) not in constants.VOLUME_TABLE[self._code] else item
        return int(constants.VOLUME_TABLE[self._code]['%d-%d-%d'%(volume, sub, item)])

class ThaiFiveBooksEngine(Engine):

    def __init__(self):
        super(ThaiFiveBooksEngine, self).__init__()
        self._code = constants.THAI_FIVE_BOOKS_CODE
        conn = sqlite3.connect(constants.THAI_FIVE_BOOKS_DB)
        self._searcher = conn.cursor()

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
        return 1

class Model(object):
    
    @property
    def Code(self):
        return self._code
        
    @Code.setter
    def Code(self, code):
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
            
    def GetTitle(self, volume=None):
        return self._engine[self._code].GetTitle(volume)

    def GetTitles(self, volume, section=None):
        return self._engine[self._code].GetTitle(volume), self._engine[self._code].GetSubtitle(volume, section)

    def GetPage(self, volume, page):
        return self._engine[self._code].GetPage(volume, page)
        
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
        
    def ConvertItemToPage(self, volume, item, sub, checked=False):
        try:            
            return int(constants.MAP_MC_TO_SIAM['v%d-%d-i%d'%(volume, sub, item)]) if checked else constants.BOOK_ITEMS[self._code][volume][sub][item][0]
        except KeyError, e:
            return 0

    def ConvertVolume(self, volume, item, sub):
        return self._engine[self._code].ConvertVolume(volume, item, sub)

    def __init__(self, code):
        self._engine = {}
        self.Code = code

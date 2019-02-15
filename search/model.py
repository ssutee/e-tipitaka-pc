#-*- coding:utf-8 -*-

import threads, utils, constants
import wx, os.path, sys, math, sqlite3


import i18n
_ = i18n.language.ugettext

from pony.orm import Database, Required, Optional, db_session, select, desc, LongUnicode, Set

db = Database('sqlite', constants.DATA_DB, create_db=True)

class History(db.Entity):
    keywords = Required(unicode)
    total = Required(int)
    code = Required(unicode)
    read = Optional(LongUnicode)
    skimmed = Optional(LongUnicode)
    pages = Optional(LongUnicode)
    notes = Optional(LongUnicode)

class SearchAndCompareHistory(db.Entity):
    keywords1 = Required(unicode)
    keywords2 = Required(unicode)
    code1 = Required(unicode)
    code2 = Required(unicode)
    total = Required(int)
    count1 = Optional(int)
    count2 = Optional(int)
    readItems = Set('SearchAndCompareHistoryReadItem')

class SearchAndCompareHistoryReadItem(db.Entity):
    history = Optional(SearchAndCompareHistory)
    row = Required(int)
    col = Required(int)

db.generate_mapping(create_tables=True)

class Model(object):

    @staticmethod
    def GetHistoryListItems(index, alphabetSort=True, text=''):
        return [u'%s (%d)' % (h.keywords, h.total) for h in Model.GetHistories(index, alphabetSort, text)]

    @staticmethod
    def GetHistories(index, alphabetSort=True, text=''):
        sortDesc = (lambda h: h.keywords) if alphabetSort else (lambda h: desc(h.id))
        results, start, page = [], 0, 500
        while True:
            query = select(h for h in History if h.code == constants.CODES[constants.LANGS_ORDER[index]] and text in h.keywords).order_by(sortDesc)[start:start+page]
            if len(query) == 0: 
                break
            results += list(query)
            start += page
        return results
        
    def __init__(self, delegate):
        self._delegate = delegate
        self._volumes = []
        self._selectedVolumes = []
        self._results = []
        self._clickedPages = []
        self._readItems = []
        self._skimmedItems = []
        self._selectedItem = -1
        self._data = {}
        self._spellChecker = None
        self._keywords = u''
        self._currentPagination = 0
        self._mode = constants.MODE_ALL        

    @property
    def CurrentPagination(self):
        return self._currentPagination
        
    @CurrentPagination.setter
    def CurrentPagination(self, value):
        self._currentPagination = value

    @property
    def Delegate(self):
        return self._delegate

    @Delegate.setter
    def Delegate(self, delegate):
        self._delegate = delegate

    @property    
    def Volumes(self):
        return self._volumes

    @Volumes.setter
    def Volumes(self, volumes):
        self._volumes = volumes

    @property
    def SelectedVolumes(self):
        return self._selectedVolumes
        
    @SelectedVolumes.setter
    def SelectedVolumes(self, volumes):
        self._selectedVolumes = volumes
        
    @property
    def Mode(self):
        return self._mode
        
    @Mode.setter
    def Mode(self, mode):
        self._mode = mode

    @property
    def Results(self):
        return self._results

    @Results.setter
    def Results(self, results):
        self._results = results
        
    @property
    def Keywords(self):
        return self._keywords
        
    @Keywords.setter
    def Keywords(self, keywords):
        self._keywords = keywords
        
    @property
    def CleanKeywords(self):
        return ' '.join(filter(lambda x:x.find('v:') != 0, self.Keywords.split()))

    @property
    def SpellChecker(self):
        return self._spellChecker

    def HasDisplayResult(self, key):
        return key in self._data
        
    def GetDisplayResult(self, key):
        return self._data.get(key, [])
        
    def SaveDisplayResult(self, items, key):
        self._data[key] = items

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        raise NotImplementedError('Subclass needs to implement this method!')

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):
        raise NotImplementedError('Subclass needs to implement this method!')

    def GetSectionBoundary(self, position):
        if position == 0:
            return 8
        if position == 1:
            return 33
        return 45

    def Read(self, code, volume, page, idx):
        if self.Code != code:
            return

        self._selectedItem = idx

        if idx > 0 and idx not in  self._readItems:
            if idx in self._skimmedItems:                
                self._skimmedItems.remove(idx)            
            self._readItems.append(idx)
        
        self.ReloadDisplay()        

    def Skim(self, volume, page, code):
        if self.Code != code:
            return

        for idx, result in enumerate(self._results):
            if int(result['volume']) == volume and int(result['page']) == page:
                if (idx+1) not in self._skimmedItems and (idx+1) not in self._readItems:
                    self._skimmedItems.append(idx+1)
                    self.ReloadDisplay()

    def GetNote(self, idx):
        return self._notes.get(idx, ('', 0))

    def TakeNote(self, idx, note ,state, code):
        if self.Code != code:
            return
        self._notes[idx] = (note, state)
        self.ReloadDisplay()

    def ReloadDisplay(self):
        self.Display(self._currentPagination)

    def Search(self, keywords, buddhawaj=False):
        self._keywords = keywords
        self._currentPagination = 0        
        self._clickedPages = []
        self._readItems = []
        self._skimmedItems = []
        self._selectedItem = -1
        self._data = {}
                
        self.CreateSearchThread(keywords, self._volumes if self._mode == constants.MODE_ALL else self._selectedVolumes, 
            self._delegate, buddhawaj).start()
        
    def Display(self, current):
        if len(self._results) == 0:
            return
                        
        if current != self._currentPagination:
            self._currentPagination = current
            if hasattr(self._delegate, 'SaveScrollPosition'):
                self._delegate.SaveScrollPosition(0)
        self.CreateDisplayThread(self._results, self._keywords, self._delegate, self.GetMark(current), current).start()
        if current not in self._clickedPages:
            self._clickedPages.append(current)
        self.SaveHistory(self.Code)
        
    @db_session
    def LoadHistory(self, keywords, code, total):        
        history = History.get(keywords=keywords, code=code)
        if history is None:
            history = History(keywords=keywords, code=code, total=total, read=u'', skimmed=u'', pages=u'')

        self._selectedItem = -1
        self._readItems = map(int, history.read.split(',')) if len(history.read) > 0 else []            
        self._skimmedItems = map(int, history.skimmed.split(',')) if len(history.skimmed) > 0 else []
        self._clickedPages = map(int, history.pages.split(',')) if history.pages is not None and len(history.pages) > 0 else []
        self._notes = {}
        if history.notes is not None and len(history.notes) > 0:
            for token in history.notes.split('~'):
                idx,note,state = token.split('|')
                self._notes[int(idx)] = (note, int(state))

    @db_session
    def SaveHistory(self, code):
        history = History.get(keywords=self._keywords, code=code) if self._keywords is not None and len(self._keywords) > 0 else None
        if history and self.Code == code:
            conn = sqlite3.connect(constants.DATA_DB)
            cursor = conn.cursor()
            
            readItems = ','.join(map(str, self._readItems))
            skimmedItems = ','.join(map(str, self._skimmedItems))
            clickedPages = ','.join(map(str, self._clickedPages))
            
            notes = ''
            tmp = []            
            for idx in self._notes:
                tmp.append('%d|%s|%d' % (idx, self._notes[idx][0], self._notes[idx][1]))
            if len(tmp) > 0:
                notes = '~'.join(tmp)

            cursor.execute('UPDATE History SET read=? WHERE keywords=? AND code=?', (readItems, self._keywords, code))
            cursor.execute('UPDATE History SET skimmed=? WHERE keywords=? AND code=?', (skimmedItems, self._keywords, code))
            cursor.execute('UPDATE History SET pages=? WHERE keywords=? AND code=?', (clickedPages, self._keywords, code))
            cursor.execute('UPDATE History SET notes=? WHERE keywords=? AND code=?', (notes, self._keywords, code))
            conn.commit()
            conn.close()
                    
    def DisplayNext(self):
        self.Display(self._currentPagination+1)

    def DisplayPrevious(self):
        self.Display(self._currentPagination-1)

    def NotFoundMessage(self):
        raise NotImplementedError('Subclass needs to implement this method!')

    def MakeHtmlSuggestion(self, found=False):
        html = ''
        for word in self.GetSuggestion():
            html += u'<a href="s:%s">%s</a> '%(word, word)
        return '<br>' if html == '' else ('<br><div>%s: %s</div><br>' if found else '<br><br><div>%s: %s</div><br>') % (_('You mean?'), html)
        
    def _MakeItemsLabel(self, items):
        tokens = map(utils.ArabicToThai, items.split())
        return u'%s - %s'%(tokens[0], tokens[-1]) if len(tokens) > 1 else tokens[0]
        
    def _MakeHtmlItemInfo(self, volume, items):
        return '<font size="4" color="%s">%s %s %s</font>' % (self._GetColorCode(volume), 
            self.GetBookName(volume), _('Item'), self._MakeItemsLabel(items))                                
                
    def _MakeHtmlEntry(self, idx, volume, page):
        info = ''        
        if idx in self._readItems:
            info = _('(read)')
        elif idx in self._skimmedItems:
            info = _('(skimmed)')

        link = u'<font color="black"><b>%s</b></font>'        
        if idx == self._selectedItem:
            link = u'<table><tr><td bgcolor="#4688DF"><font color="white"><b>%s</b></font></td></tr></table>'
            info = ''
        elif idx in self._readItems or idx in self._skimmedItems:
            link = u'<font color="grey" bgcolor="#00FF00">%s</font>'        
            
        return u'''
            <font size="4">
                <a href="p:%s_%s_%s_%d_%d_%d_%d">%s</a> <font color="red">%s</font><br>
            </font>''' % (volume, page, self.Code, self.CurrentPagination, 
                constants.ITEMS_PER_PAGE, len(self._results), idx, 
                link % (self._GetEntry(idx, volume ,page)), info)
    
    def _MakeHtmlPagination(self, pages, current):
        text = u'<p>'
        for idx in range(1, pages+1):            
            if idx == current:
                text += u'<span><b><font color="blue">%s</font></b></span> '%(utils.ArabicToThai(unicode(idx)))
            else:
                p = u'<a href="n:%d_%d_%d"><font color="%s">%s</font></a>' % \
                    (idx, constants.ITEMS_PER_PAGE, len(self._results), 
                    "black" if idx not in self._clickedPages else "#BFBFBF", utils.ArabicToThai(unicode(idx)))
                text += u'<span>' + p + u'</span> '                
        text += '</p>'
        return '<div align="center">'+_('All results') + text + '</div>'
                
    def _MakeHtmlSummary(self):
        counts = self._GetResultSectionCounts()
        return u'''
            <div align="center">
                <table cellpadding="0">
                    <tr>
                        <th align="center"><b><font color="%s">%s</font></b></th>
                        <th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
                        <th align="center"><b><font color="%s">%s</font></b></th>
                        <th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
                        <th align="center"><b><font color="%s">%s</font></b></th>                                                        
                    </tr>
                    <tr>
                        <td align="center">%s</td>
                        <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>                            
                        <td align="center">%s</td>
                        <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>                            
                        <td align="center">%s</td>                                                                                
                    </tr>
                </table>
            </div><br/><p/>
        ''' % (self.ColorCode(0), self.SectionName(0), 
               self.ColorCode(1), self.SectionName(1), 
               self.ColorCode(2), self.SectionName(2),
               utils.ArabicToThai(unicode(counts[0])) + ' ' + _('Page unit'), 
               utils.ArabicToThai(unicode(counts[1])) + ' ' + _('Page unit'), 
               utils.ArabicToThai(unicode(counts[2])) + ' ' + _('Page unit'))        
               
    def SectionName(self, index):
        if index == 0:
            return _('Section 1')
        if index == 1:
            return _('Section 2')
        return _('Section 3')
        
    def ColorCode(self, index):
        if index == 0:
            return "#1e90ff"
        if index == 1:
            return "#ff4500"
        return "#a020f0"
               
    def _MakeHtmlHeader(self, mark):
        template = u'<div align="center"><font size="3" color="brown">%s</font></div>' % \
            _('Search results %s - %s of %s for keyword "%s"')            
        return template % (utils.ArabicToThai(unicode(mark[0]+1)), utils.ArabicToThai(unicode(mark[1])),
            utils.ArabicToThai(unicode(len(self._results))), self.CleanKeywords)        

    def _GetEntry(self, idx, volume, page):
        return u'%s. %s %s %s %s' % (utils.ArabicToThai(unicode(idx)), _('Tipitaka volume'),
            utils.ArabicToThai(volume), _('Page'), utils.ArabicToThai(page))
                
    def _GetColorCode(self, volume):
        volume = int(volume)
        if volume <= self.GetSectionBoundary(0):
            return self.ColorCode(0)
        if volume <= self.GetSectionBoundary(1):
            return self.ColorCode(1)
        return self.ColorCode(2)
        
    def _GetResultSectionCounts(self, section=None):
        counts = [0,0,0]
        for result in self._results:
            volume = int(result['volume'])
            if volume <= self.GetSectionBoundary(0):
                counts[0] += 1
            elif volume <= self.GetSectionBoundary(1):
                counts[1] += 1
            else:
                counts[2] += 1
        return counts if section == None else counts[section]

    def GetMark(self, current):
        start = (current-1) * constants.ITEMS_PER_PAGE
        end = (current-1) * constants.ITEMS_PER_PAGE + constants.ITEMS_PER_PAGE        
        return (start, len(self._results) if len(self._results) < end else end)
        
    def GetPages(self):
        return int(math.ceil(1.0*len(self._results)/constants.ITEMS_PER_PAGE))
                
    def _MakeHtmlExcerpts(self, excerpts):
        return u'<font size="4">%s</font><br>'%(excerpts) 
        
    def MakeHtmlResults(self, current):
        mark = self.GetMark(current)        
        pages = self.GetPages()        
        text = ''        
        for idx, volume, page, items, excerpts in self.GetDisplayResult('%d:%d'%mark):
            stateImage = ''
            noteText = ''
            if idx in self._notes:
                state = self._notes[idx][1]
                if state == 1:
                    stateImage = '<img src="memory:not-ok.png">'
                elif state == 2:
                    stateImage = '<img src="memory:ok.png">'                

                if len(self._notes[idx][0]) > 0:
                    noteText = '(' + self._notes[idx][0] + ')'

            note = '<a href="note:%d_%s_%s_%s"><img src="memory:edit-notes.png"></a> %s %s' % (idx, volume, page, self.Code, stateImage, noteText)
            text += u'<div>' + self._MakeHtmlEntry(idx, volume, page) + \
                self._MakeHtmlExcerpts(excerpts) + self._MakeHtmlItemInfo(volume, items) + \
                u'</div> %s <br>' % (note)
                
        return u'<html><body bgcolor="%s">'%(utils.LoadThemeBackgroundHex(constants.SEARCH)) + self._MakeHtmlSummary() + self._MakeHtmlHeader(mark) + self.MakeHtmlSuggestion(found=True) \
            + text + '<br>' + self._MakeHtmlPagination(pages, current) + '</body></html>'
        
    def GetSuggestion(self):
        keywords = self._keywords.replace('+',' ')
        if len(keywords.split()) > 1:
            return []
        return self._spellChecker.suggest(keywords, number=5) if self._spellChecker else []
        
    def GetBookName(self, volume):
        return constants.BOOK_NAMES['%s_%s' % (self.Code, str(volume).lstrip('0'))].decode('utf8','ignore')
        
    def GetBookNames(self):
        return [self.GetBookName(volume+1) for volume in range(len(self._volumes))]

    def ConvertSpecialCharacters(self, text):
        return text

    def HasBuddhawaj(self):
        return False

    def HasVolumeSelection(self):
        return True

class SearchModelCreator(object):
    
    @staticmethod
    def Create(delegate, index):
        code = constants.CODES[constants.LANGS_ORDER[index]]

        if code == constants.THAI_ROYAL_CODE:
            return ThaiRoyalSearchModel(delegate)
        if code == constants.PALI_SIAM_CODE:
            return PaliSiamSearchModel(delegate)
        if code == constants.THAI_WATNA_CODE:
            return ThaiWatnaSearchModel(delegate)
        if code == constants.THAI_MAHAMAKUT_CODE:
            return ThaiMahaMakutSearchModel(delegate)
        if code == constants.THAI_MAHACHULA_CODE:
            return ThaiMahaChulaSearchModel(delegate)
        if code == constants.THAI_SUPREME_CODE:
            return ThaiSupremeSearchModel(delegate)
        if code == constants.THAI_FIVE_BOOKS_CODE:
            return ThaiFiveBooksSearchModel(delegate)
        if code == constants.ROMAN_SCRIPT_CODE:
            return RomanScriptSearchModel(delegate)
        if code == constants.THAI_POCKET_BOOK_CODE:
            return ThaiPocketBookSearchModel(delegate)
        if code == constants.PALI_MAHACHULA_CODE:
            return PaliMahaChulaSearchModel(delegate)
        if code == constants.THAI_VINAYA_CODE:
            return ThaiVinayaSearchModel(delegate)
        if code == constants.PALI_SIAM_NEW_CODE:
            return PaliSiamNewSearchModel(delegate)
        return None

class ThaiRoyalSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_ROYAL_CODE
    
    def __init__(self, delegate):
        super(ThaiRoyalSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.THAI_SPELL_CHECKER
    
    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiRoyalSearchThread(keywords, volumes, delegate)
        
    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiRoyalDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai Royal')) % (self._keywords) )

class PaliSiamSearchModel(Model):

    @property
    def Code(self):
        return constants.PALI_SIAM_CODE

    def __init__(self, delegate):
        super(PaliSiamSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.PALI_SPELL_CHECKER

    @property
    def Keywords(self):
        return utils.ConvertToPaliSearch(self._keywords)

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        keywords = utils.ConvertToThaiSearch(keywords, True)
        return threads.PaliSiamSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.PaliSiamDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Pali Siam')) % (self._keywords))
        
    def GetSuggestion(self):
        return map(utils.ConvertToPaliSearch, super(PaliSiamSearchModel, self).GetSuggestion())
        
    def ConvertSpecialCharacters(self, text):
        return utils.ConvertToPaliSearch(text, True)        
        
class PaliSiamNewSearchModel(PaliSiamSearchModel):
    
    @property
    def Code(self):
        return constants.PALI_SIAM_NEW_CODE

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        keywords = utils.ConvertToThaiSearch(keywords, True)
        return threads.PaliSiamNewSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.PaliSiamDisplayThread(results, keywords, delegate, mark, current)


    def GetBookName(self, volume):
        return constants.BOOK_NAMES['pali_%s' % (str(volume).lstrip('0'))].decode('utf8','ignore')


class ThaiWatnaSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_WATNA_CODE

    def __init__(self, delegate):
        super(ThaiWatnaSearchModel, self).__init__(delegate)
        self._volumes = range(33)
        self._spellChecker = constants.THAI_SPELL_CHECKER

    def HasBuddhawaj(self):
        return True

    def HasVolumeSelection(self):
        return False        

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiWatnaSearchThread(keywords, volumes, delegate, buddhawaj=buddhawaj)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiWatnaDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Buddhawajana Pitaka')) % (self._keywords) )        

    def _GetEntry(self, idx, volume, page):
        return u'%s. %s %s %s %s' % (utils.ArabicToThai(unicode(idx)), u'พุทธวจนปิฎก เล่มที่',
            utils.ArabicToThai(volume), _('Page'), utils.ArabicToThai(page))

class ThaiMahaChulaSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_MAHACHULA_CODE

    def __init__(self, delegate):
        super(ThaiMahaChulaSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.THAI_SPELL_CHECKER
    
    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiMahaChulaSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiMahaChulaDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai MahaChula')) % (self._keywords) )        
        
class ThaiSupremeSearchModel(Model):
    @property
    def Code(self):
        return constants.THAI_SUPREME_CODE

    def __init__(self, delegate):
        super(ThaiSupremeSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.THAI_SPELL_CHECKER

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiSupremeSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiSupremeDisplayThread(results, keywords, delegate, mark, current)


    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((u'ไม่พบ %s ในพระไตรปิฎก (ภาษาไทย ฉบับมหาเถรฯ)') % (self._keywords))


class PaliMahaChulaSearchModel(Model):

    @property
    def Code(self):
        return constants.PALI_MAHACHULA_CODE

    def __init__(self, delegate):
        super(PaliMahaChulaSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.PALI_SPELL_CHECKER
    
    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.PaliMahaChulaSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.PaliMahaChulaDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Pali MahaChula')) % (self._keywords) )        

    def GetBookName(self, volume):
        return constants.BOOK_NAMES['pali_%s' % (str(volume).lstrip('0'))].decode('utf8','ignore')


class ThaiMahaMakutSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_MAHAMAKUT_CODE

    def __init__(self, delegate):
        super(ThaiMahaMakutSearchModel, self).__init__(delegate)
        self._volumes = range(91)
        self._spellChecker = constants.THAI_SPELL_CHECKER
    
    def GetSectionBoundary(self, position):
        if position == 0:
            return 10
        if position == 1:
            return 74
        return 91
        
    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiMahaMakutSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiMahaMakutDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai MahaMakut')) % (self._keywords) )

class ScriptSearchModel(Model):

    def __init__(self, delegate):
        super(ScriptSearchModel, self).__init__(delegate)
        self._volumes = range(61)
        self._spellChecker = None

    def GetSectionBoundary(self, position):
        if position == 0:
            return 5
        if position == 1:
            return 48
        return 61

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):
        return threads.ScriptDisplayThread(results, keywords, delegate, mark, current)

class RomanScriptSearchModel(ScriptSearchModel):

    @property
    def Code(self):
        return constants.ROMAN_SCRIPT_CODE

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.RomanScriptSearchThread(keywords, volumes, delegate)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Tipitaka Roman Script')) % (self._keywords) )

    def GetBookName(self, volume):
        return constants.ROMAN_SCRIPT_TITLES[volume][1]

    def HasVolumeSelection(self):
        return True                


class ThaiScriptSearchModel(ScriptSearchModel):

    @property
    def Code(self):
        return constants.THAI_SCRIPT_CODE


    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiScriptSearchThread(keywords, volumes, delegate)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Tipitaka Thai Script')) % (self._keywords) )

    def GetBookName(self, volume):
        return constants.THAI_SCRIPT_TITLES[volume][1]

    def HasVolumeSelection(self):
        return False                

class ThaiVinayaSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_VINAYA_CODE

    def __init__(self, delegate):
        super(ThaiVinayaSearchModel, self).__init__(delegate)
        self._volumes = range(11)
        self._spellChecker = constants.THAI_SPELL_CHECKER

    def HasVolumeSelection(self):
        return False

    def GetSectionBoundary(self, position):
        return 0

    def _GetColorCode(self, volume):
        return None

    def _GetResultSectionCounts(self):
        return []

    def _MakeHtmlItemInfo(self, volume, items):
        return ''
        
    def _MakeHtmlSummary(self):
        return ''        

    def HasBuddhawaj(self):
        return True

    def _GetEntry(self, idx, volume, page):
        return u'%s. %s %s %s' % (utils.ArabicToThai(unicode(idx)), 
            self.GetBookName(volume), _('Page'), utils.ArabicToThai(page))

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiVinayaSearchThread(keywords, volumes, delegate, buddhawaj=buddhawaj)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiVinayaDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((u'ไม่พบ %s ในหนังสืออริยวินัย') % (self._keywords) )

class ThaiPocketBookSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_POCKET_BOOK_CODE

    def __init__(self, delegate):
        super(ThaiPocketBookSearchModel, self).__init__(delegate)
        self._volumes = range(18)
        self._spellChecker = constants.THAI_SPELL_CHECKER

    def HasVolumeSelection(self):
        return False

    def GetSectionBoundary(self, position):
        return 0

    def _GetColorCode(self, volume):
        return None

    def _GetResultSectionCounts(self):
        return []

    def _MakeHtmlItemInfo(self, volume, items):
        return ''
        
    def _MakeHtmlSummary(self):
        return ''        

    def HasBuddhawaj(self):
        return True

    def _GetEntry(self, idx, volume, page):
        return u'%s. %s %s %s' % (utils.ArabicToThai(unicode(idx)), 
            self.GetBookName(volume), _('Page'), utils.ArabicToThai(page))

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiPocketBookSearchThread(keywords, volumes, delegate, buddhawaj=buddhawaj)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiPocketBookDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai Pocket Book')) % (self._keywords) )


class ThaiFiveBooksSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_FIVE_BOOKS_CODE

    def __init__(self, delegate):
        super(ThaiFiveBooksSearchModel, self).__init__(delegate)
        self._volumes = range(5)
        self._spellChecker = constants.THAI_SPELL_CHECKER

    def HasVolumeSelection(self):
        return False                

    def GetSectionBoundary(self, position):
        return 0

    def _GetColorCode(self, volume):
        return None

    def _GetResultSectionCounts(self):
        return []

    def _MakeHtmlItemInfo(self, volume, items):
        return ''
        
    def _MakeHtmlSummary(self):
        return ''        

    def _GetEntry(self, idx, volume, page):
        return u'%s. %s %s %s' % (utils.ArabicToThai(unicode(idx)), 
            self.GetBookName(volume), _('Page'), utils.ArabicToThai(page))

    def GetBookName(self, volume):
        return constants.FIVE_BOOKS_NAMES[int(volume)-1]

    def CreateSearchThread(self, keywords, volumes, delegate, buddhawaj=False):
        return threads.ThaiFiveBooksSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiFiveBooksDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai Five Books')) % (self._keywords) )


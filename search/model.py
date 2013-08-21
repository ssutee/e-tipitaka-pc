#-*- coding:utf-8 -*-

import threads, utils, constants
import wx

import i18n
_ = i18n.language.ugettext

class Model(object):

    def __init__(self, delegate):
        self._delegate = delegate
        self._volumes = []
        self._selectedVolumes = []
        self._results = []
        self._clickedPages = []
        self._readItems = []
        self._data = {}
        self._spellChecker = None
        self._keywords = None
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

    def CreateSearchThread(self, keywords, volumes, delegate):
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
        if idx not in  self._readItems:
            self._readItems.append(idx)
            self._ReloadDisplay()
        print 'open'
            
    def _ReloadDisplay(self):
        self.Display(self._currentPagination)

    def Search(self, keywords):
        self._keywords = keywords
        self._currentPagination = 0        
        self._clickedPages = []
        self._readItems = []
        self._data = {}
                
        self.CreateSearchThread(keywords, self._volumes if self._mode == constants.MODE_ALL else self._selectedVolumes, 
            self._delegate).start()
        
    def Display(self, current):  
        if current != self._currentPagination:
            self._currentPagination = current
            if hasattr(self._delegate, 'SaveScrollPosition'):
                self._delegate.SaveScrollPosition(0)

        self.CreateDisplayThread(self._results, self._keywords, self._delegate, self.GetMark(current), current).start()
        if current not in self._clickedPages:
            self._clickedPages.append(current)
        
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
        return u'''
            <font size="4">
                <a href="p:%s_%s_%s_%d_%d_%d_%d">%s</a> <font color="red">%s</font><br>
            </font>''' % (volume, page, self.Code, self.CurrentPagination, 
                constants.ITEMS_PER_PAGE, len(self._results), idx, 
                self._GetEntry(idx, volume ,page), _('(read)') if idx in self._readItems else '' )
    
    def _MakeHtmlPagination(self, pages, current):
        text = _('All results') + '<br>'
        for idx in range(1, pages+1):            
            if idx == current:
                text += u'<b>%s</b> '%(utils.ArabicToThai(unicode(idx)))
            else:
                p = u'<a href="n:%d_%d_%d">%s</a> ' % \
                    (idx, constants.ITEMS_PER_PAGE, len(self._results), utils.ArabicToThai(unicode(idx)))
                text += p if idx not in self._clickedPages else ('<b><i>%s</i></b>' % (p))                    
        return '<div align="center">' + text + '</div>'        
                
    def _MakeHtmlSummary(self):
        counts = self._GetResultSectionCounts()
        return u'''
            <div align="center">
                <table cellpadding="0">
                    <tr>
                        <th align="center"><b><font color="#1e90ff">%s</font></b></th>
                        <th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
                        <th align="center"><b><font color="#ff4500">%s</font></b></th>
                        <th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
                        <th align="center"><b><font color="#a020f0">%s</font></b></th>                                                        
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
        ''' % (_('Section 1'), _('Section 2'), _('Section 3'),
               utils.ArabicToThai(unicode(counts[0])) + ' ' + _('Page unit'), 
               utils.ArabicToThai(unicode(counts[1])) + ' ' + _('Page unit'), 
               utils.ArabicToThai(unicode(counts[2])) + ' ' + _('Page unit'))        
               
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
            return "#1e90ff"
        if volume <= self.GetSectionBoundary(1):
            return "#ff4500"
        return "#a020f0"
        
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
        pages = len(self._results)/constants.ITEMS_PER_PAGE
        return pages if len(self._results) == 0 else pages + 1
        
        
    def _MakeHtmlExcerpts(self, excerpts):
        return u'<font size="4">%s</font><br>'%(excerpts) 
        
    def MakeHtmlResults(self, current):
        mark = self.GetMark(current)        
        pages = self.GetPages()        
        text = ''
        for idx, volume, page, items, excerpts in self.GetDisplayResult('%d:%d'%mark):
            text += u'<div>' + self._MakeHtmlEntry(idx, volume, page) + \
                self._MakeHtmlExcerpts(excerpts) + self._MakeHtmlItemInfo(volume, items) + u'</div><br>'
                
        return self._MakeHtmlSummary() + self._MakeHtmlHeader(mark) + self.MakeHtmlSuggestion(found=True) \
            + text + '<br>' + self._MakeHtmlPagination(pages, current);
        
    def GetSuggestion(self):
        keywords = self._keywords.replace('+',' ')
        if len(keywords.split()) > 1:
            return []
        return self._spellChecker.suggest(keywords, number=5)     
        
    def GetBookName(self, volume):
        return constants.BOOK_NAMES['%s_%s' % (self.Code, str(volume))].decode('utf8','ignore')
        
    def GetBookNames(self):
        return [self.GetBookName(volume+1) for volume in range(self.GetSectionBoundary(2))]

class SearchModelCreator(object):
    
    @staticmethod
    def create(delegate, index):
        if index == 0:
            return ThaiRoyalSearchModel(delegate)
        if index == 1:
            return PaliSiamSearchModel(delegate)
        if index == 2:
            return ThaiMahaMakutSearchModel(delegate)
        if index == 3:
            return ThaiMahaChulaSearchModel(delegate)
        if index == 4:
            return ThaiFiveBooksSearchModel(delegate)
        return None

class ThaiRoyalSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_ROYAL_CODE
    
    def __init__(self, delegate):
        super(ThaiRoyalSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.THAI_SPELL_CHECKER
    
    def CreateSearchThread(self, keywords, volumes, delegate):
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
    
    def CreateSearchThread(self, keywords, volumes, delegate):
        if 'wxMac' not in wx.PlatformInfo:
            keywords = utils.ConvertToPaliSearch(keywords)
        return threads.PaliSiamSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.PaliSiamDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Pali Siam')) % (self._keywords))
        
    def GetSuggestion(self):
        return map(utils.ConvertToPaliSearch, super(PaliSiamSearchModel, self).GetSuggestion())
        
class ThaiMahaChulaSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_MAHACHULA_CODE

    def __init__(self, delegate):
        super(ThaiMahaChulaSearchModel, self).__init__(delegate)
        self._volumes = range(45)
        self._spellChecker = constants.THAI_SPELL_CHECKER
    
    def CreateSearchThread(self, keywords, volumes, delegate):
        return threads.ThaiMahaChulaSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiMahaChulaDisplayThread(results, keywords, delegate, mark, current)
        
    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai MahaChula')) % (self._keywords) )        
        
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
        
    def CreateSearchThread(self, keywords, volumes, delegate):
        return threads.ThaiMahaMakutSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiMahaMakutDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai MahaMakut')) % (self._keywords) )

class ThaiFiveBooksSearchModel(Model):

    @property
    def Code(self):
        return constants.THAI_FIVE_BOOKS_CODE

    def __init__(self, delegate):
        super(ThaiFiveBooksSearchModel, self).__init__(delegate)
        self._volumes = range(5)
        self._spellChecker = constants.THAI_SPELL_CHECKER

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

    def CreateSearchThread(self, keywords, volumes, delegate):
        return threads.ThaiFiveBooksSearchThread(keywords, volumes, delegate)

    def CreateDisplayThread(self, results, keywords, delegate, mark, current):        
        return threads.ThaiFiveBooksDisplayThread(results, keywords, delegate, mark, current)

    def NotFoundMessage(self):
        return u'<div align="center"><h2>%s</h2></div>' % ((_('Not found %s in Thai Five Books')) % (self._keywords) )

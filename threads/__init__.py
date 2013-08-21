import wx
import threading, sqlite3, os.path, sys
from cgi import escape as htmlescape

import constants, utils

from whoosh.highlight import highlight, HtmlFormatter, SimpleFragmenter
from whoosh.analysis import NgramTokenizer
from formatters import MyHtmlFormatter

class SearchThread(threading.Thread):
    
    def __init__(self, keywords, volumes, delegate):
        super(SearchThread, self).__init__()
        self._delegate = delegate
        self._keywords = keywords
        self._volumes = volumes    
    
    def run(self):
        conn = sqlite3.connect(self.Database)
        searcher = conn.cursor()
        terms = map(lambda term: term.replace('+',' '),self._keywords.split())
        
        query, args = self.PrepareStatement(terms)

        if hasattr(self._delegate, 'SearchWillStart'):
            wx.CallAfter(self._delegate.SearchWillStart)
        
        results = []
        for result in searcher.execute(query, args):
            results.append(self.ProcessResult(result))
        
        if hasattr(self._delegate, 'SearchDidFinish'):
            wx.CallAfter(self._delegate.SearchDidFinish, results)
        
    def ProcessResult(self, result):
        r = {}
        r['volume'] = result[0]
        r['page'] = result[1]
        r['items'] = result[2]
        r['content'] = result[3]
        return r    
    
    def PrepareStatement(self, terms):
        query = 'SELECT * FROM %s WHERE '%(self.Code)
        args = tuple([])
        for term in terms:
            if '|' in term:
                tmp = ''
                for t in term.split('|'):
                    if len(t.strip()) > 0:
                        tmp += 'content LIKE ? OR '
                        args += ('%'+t+'%',)
                if len(tmp) > 0:
                    query += ' (%s) AND' % (tmp.rstrip(' OR '))
            else:
                query += ' content LIKE ? AND'
                args += ('%'+term+'%',)
        
        if len(self._volumes) > 0:
            query += ' ('
            query += "volumn = ?"
            args += ("%02d"%(self._volumes[0]+1), )
            for p in self._volumes[1:]:                
                query += " OR volumn = ?"
                args += ("%02d" % (p+1), )
            query += ')'
            
        query = query.rstrip(' AND')

        return query, args
        
class ThaiFiveBooksSearchThread(SearchThread):
    
    @property
    def Code(self):
        return constants.THAI_FIVE_BOOKS_CODE
    
    @property
    def Database(self):
        return constants.THAI_FIVE_BOOKS_DB    
        
    def ProcessResult(self, result):
        r = {}
        r['volume'] = result[0]
        r['page'] = result[1]
        r['content'] = result[3]
        return r
        
    def PrepareStatement(self, terms):
        query = 'SELECT * FROM speech WHERE '
        args = tuple([])
        for term in terms:
            if term.find('v:') == 0:
                try:
                    query += ' ('
                    for vol in term[2:].split(','):
                        if '-' in vol and len(vol.split('-')) == 2:
                            start, end = map(int, vol.split('-'))
                            for i in xrange(start, end+1, 1):
                                query += 'book = ? OR '
                                args += (i,)
                        else:
                            query += 'book = ? OR '
                            args += (int(vol),)
                    query = query.rstrip(' OR ') + ') AND'
                except ValueError, e:
                    pass                    
            elif '|' in term:
                tmp = ''
                for t in term.split('|'):
                    if len(t.strip()) > 0:
                        tmp += 'content LIKE ? OR '
                        args += ('%'+t+'%',)
                if len(tmp) > 0:
                    query += ' (%s) AND' % (tmp.rstrip(' OR'))
            else:
                query += 'content LIKE ? AND '
                args += ('%'+term+'%',)
                
        return query.rstrip(' AND'), args
    
class ThaiRoyalSearchThread(SearchThread):

    @property
    def Code(self):
        return constants.THAI_ROYAL_CODE

    @property
    def Database(self):
        return constants.THAI_ROYAL_DB    

class PaliSiamSearchThread(SearchThread):

    @property
    def Code(self):
        return constants.PALI_SIAM_CODE

    @property
    def Database(self):
        return constants.PALI_SIAM_DB    

class ThaiMahaChulaSearchThread(SearchThread):

    @property
    def Code(self):
        return constants.THAI_MAHACHULA_CODE

    @property
    def Database(self):
        return constants.THAI_MAHACHULA_DB    
        
    def ProcessResult(self, result):
        r = {}
        r['volume'] = result[0]
        r['page'] = result[1]
        r['items'] = result[2]
        r['header'] = result[3]
        r['footer'] = result[4]
        r['display'] = result[5]
        r['content'] = result[6]
        return r

class ThaiMahaMakutSearchThread(SearchThread):

    @property
    def Code(self):
        return constants.THAI_MAHAMAKUT_CODE

    @property
    def Database(self):
        return constants.THAI_MAHAMAKUT_DB    
        
    def ProcessResult(self, result):
        r = {}
        r['volume'] = result[0]
        r['volume_orig'] = result[1]
        r['page'] = result[2]
        r['items'] = result[3]
        r['content'] = result[4]
        return r

class DisplayThread(threading.Thread):
    
    def __init__(self, results, keywords, delegate, mark, current):
        threading.Thread.__init__(self)
        self._results = results
        self._keywords = keywords
        self._delegate = delegate
        self._mark = mark
        self._current = current
    
    def run(self):
        keywords = self._keywords.replace('+',' ')
        keywords = ' '.join(filter(lambda x:x.find('v:') != 0, keywords.split()))

        termset = []
        for term in keywords.split():
            termset.append(term)
        
        if hasattr(self._delegate, 'DisplayWillStart'):
            wx.CallAfter(self._delegate.DisplayWillStart)
        
        items = []
        key = '%d:%d' % (self._mark)        
        if hasattr(self._delegate, 'HasDisplayResult') and not self._delegate.HasDisplayResult(key):            
            for idx, result in enumerate(self._results[self._mark[0]:self._mark[1]]):
                excerpts = highlight(result['content'], termset,
                    NgramTokenizer(min([len(t) for t in termset]), max([len(t) for t in termset])),
                    SimpleFragmenter(size=70), MyHtmlFormatter(tagname='font', attrs='size="4" color="purple"'))
                items.append(self.ProcessResult(idx, result, self.ProcessExcerpts(excerpts)))                            

                if hasattr(self._delegate, 'DisplayDidProgress'):
                    wx.CallAfter(self._delegate.DisplayDidProgress, (idx+1))                        

            if hasattr(self._delegate, 'SaveDisplayResult'):
                self._delegate.SaveDisplayResult(items, key)    

        if hasattr(self._delegate, 'DisplayDidFinish'):
            wx.CallAfter(self._delegate.DisplayDidFinish, key, self._current)
        
    def ProcessExcerpts(self, excerpts):
        return excerpts
        
    def ProcessResult(self, idx, result, excerpts):
        return (self._mark[0]+idx+1, result['volume'].lstrip(u'0'), result['page'].lstrip(u'0'), result['items'], excerpts)
        
class PaliSiamDisplayThread(DisplayThread):
    
    def ProcessExcerpts(self, excerpts):
        if 'wxMac' not in wx.PlatformInfo:
            return utils.ConvertToPaliSearch(excerpts)
        return excerpts

class ThaiFiveBooksDisplayThread(DisplayThread):
    
    def ProcessResult(self, idx, result, excerpts):
        return (self._mark[0]+idx+1, unicode(result['volume']), unicode(result['page']), u'0', excerpts)
        
class ThaiRoyalDisplayThread(DisplayThread):
    pass
    
class ThaiMahaMakutDisplayThread(DisplayThread):
    pass
    
class ThaiMahaChulaDisplayThread(DisplayThread):
    pass

#-*- coding:utf-8 -*-

import unittest
import threads
import Queue as queue

class TestSearchThread(unittest.TestCase):
            
    def testSearch1(self):
        q = queue.Queue()
        thread = self.cls(self.keywords, [], None, q)
        thread.start()
        result = q.get()        
        self.assertEqual(self.keywords, result[1])
        self.assertEqual(self.expected, len(result[0]))
        
    def testSearch2(self):
        q = queue.Queue()
        keywords = u'not found'
        thread = self.cls(keywords, [], None, q)
        thread.start()
        result = q.get()        
        self.assertEqual(keywords, result[1])
        self.assertEqual(0, len(result[0]))        

class TestThaiRoyalSearchThread(TestSearchThread):    
    
    def __init__(self, methodName):
        super(TestThaiRoyalSearchThread, self).__init__(methodName)
        self.cls = threads.ThaiRoyalSearchThread
        self.keywords = u'กรรม'
        self.expected = 3184    

class TestPaliSiamSearchThread(TestSearchThread):    

    def __init__(self, methodName):
        super(TestPaliSiamSearchThread, self).__init__(methodName)
        self.cls = threads.PaliSiamSearchThread
        self.keywords = u'อานาปา'
        self.expected = 88
                    
class TestThaiMahaChulaSearchThread(TestSearchThread):
    
    def __init__(self, methodName):
        super(TestThaiMahaChulaSearchThread, self).__init__(methodName)
        self.cls = threads.ThaiMahaChulaSearchThread
        self.keywords = u'กรรม'
        self.expected = 3330

class TestThaiMahaMakutSearchThread(TestSearchThread):

    def __init__(self, methodName):
        super(TestThaiMahaMakutSearchThread, self).__init__(methodName)
        self.cls = threads.ThaiMahaMakutSearchThread
        self.keywords = u'กรรม'
        self.expected = 10785
        
class TestThaiFiveBooksSearchThread(TestSearchThread):
    
    def __init__(self, methodName):
        super(TestThaiFiveBooksSearchThread, self).__init__(methodName)
        self.cls = threads.ThaiFiveBooksSearchThread
        self.keywords = u'กรรม'
        self.expected = 300

class TestThaiScriptSearchThread(TestSearchThread):

    def __init__(self, methodName):
        super(TestThaiScriptSearchThread, self).__init__(methodName)
        self.cls = threads.ThaiScriptSearchThread
        self.keywords = u'อานาปา'
        self.expected = 65

class TestRomanScriptSearchThread(TestSearchThread):

    def __init__(self, methodName):
        super(TestRomanScriptSearchThread, self).__init__(methodName)
        self.cls = threads.RomanScriptSearchThread
        self.keywords = u'bhikkhu'
        self.expected = 2696
                    
def suite():
    suite = unittest.TestSuite()

    suite.addTest(TestThaiRoyalSearchThread('testSearch1'))
    suite.addTest(TestThaiRoyalSearchThread('testSearch2'))    

    suite.addTest(TestPaliSiamSearchThread('testSearch1'))
    suite.addTest(TestPaliSiamSearchThread('testSearch2'))    

    suite.addTest(TestThaiMahaChulaSearchThread('testSearch1'))
    suite.addTest(TestThaiMahaChulaSearchThread('testSearch2'))

    suite.addTest(TestThaiMahaMakutSearchThread('testSearch1'))
    suite.addTest(TestThaiMahaMakutSearchThread('testSearch2'))

    suite.addTest(TestThaiFiveBooksSearchThread('testSearch1'))
    suite.addTest(TestThaiFiveBooksSearchThread('testSearch2'))

    suite.addTest(TestThaiScriptSearchThread('testSearch1'))
    suite.addTest(TestThaiScriptSearchThread('testSearch2'))

    suite.addTest(TestRomanScriptSearchThread('testSearch1'))
    suite.addTest(TestRomanScriptSearchThread('testSearch2'))
    
    return suite                
                
if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())


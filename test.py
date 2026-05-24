import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3])

runner = unittest.TextTestRunner()
runner.run(alltests)

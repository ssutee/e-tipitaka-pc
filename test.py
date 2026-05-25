import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore
import tests.test_account_client
import tests.test_account_export
import tests.test_patcher
import tests.test_import_extras

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
suite4 = tests.test_account_client.suite()
suite5 = tests.test_account_export.suite()
suite6 = tests.test_patcher.suite()
suite7 = tests.test_import_extras.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5, suite6, suite7])

runner = unittest.TextTestRunner()
runner.run(alltests)

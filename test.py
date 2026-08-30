import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore
import tests.test_account_client
import tests.test_account_export
import tests.test_patcher
import tests.test_import_extras
import tests.test_build_config
import tests.test_compare_close

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
suite4 = tests.test_account_client.suite()
suite5 = tests.test_account_export.suite()
suite6 = tests.test_patcher.suite()
suite7 = tests.test_import_extras.suite()
suite8 = tests.test_build_config.suite()
suite9 = tests.test_compare_close.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5, suite6, suite7, suite8, suite9])

runner = unittest.TextTestRunner()
runner.run(alltests)

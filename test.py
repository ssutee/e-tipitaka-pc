import unittest
import tests.test_threads
import tests.test_theme
import tests.test_account_tokenstore
import tests.test_account_client

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
suite3 = tests.test_account_tokenstore.suite()
suite4 = tests.test_account_client.suite()
alltests = unittest.TestSuite([suite1, suite2, suite3, suite4])

runner = unittest.TextTestRunner()
runner.run(alltests)

import unittest
import tests.test_threads
import tests.test_theme

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
alltests = unittest.TestSuite([suite1, suite2])

runner = unittest.TextTestRunner()
runner.run(alltests)

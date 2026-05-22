import unittest
import tests.test_threads

suite1 = tests.test_threads.suite()
alltests = unittest.TestSuite([suite1])

runner = unittest.TextTestRunner()
runner.run(alltests)

from __future__ import unicode_literals
import unittest
import logging
from codeutil.tests_java_element import JavaElementRETest, \
    JavaElementFunctionsTest, JavaStrategyTest, JavaSnippetTest


logger = logging.getLogger("docs")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def suite():
    suite1 = unittest.TestLoader().loadTestsFromTestCase(JavaElementRETest)
    suite2 = \
        unittest.TestLoader().loadTestsFromTestCase(JavaElementFunctionsTest)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(JavaStrategyTest)
    suite4 = unittest.TestLoader().loadTestsFromTestCase(JavaSnippetTest)
    alltests = unittest.TestSuite([suite1, suite2, suite3, suite4])
    return alltests

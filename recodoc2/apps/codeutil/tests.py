from __future__ import unicode_literals
import unittest
import logging
from codeutil.tests_java_element import JavaElementRETest, \
    JavaElementFunctionsTest, JavaStrategyTest, JavaSnippetTest
from codeutil.tests_other_element import OtherElementTest


logger = logging.getLogger("docs")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def suite():
    suite1 = unittest.TestLoader().loadTestsFromTestCase(JavaElementRETest)
    suite2 = \
        unittest.TestLoader().loadTestsFromTestCase(JavaElementFunctionsTest)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(JavaStrategyTest)
    suite4 = unittest.TestLoader().loadTestsFromTestCase(JavaSnippetTest)
    suite5 = unittest.TestLoader().loadTestsFromTestCase(OtherElementTest)
    alltests = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5])
    return alltests

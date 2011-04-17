from __future__ import unicode_literals
import unittest
import logging
from codeutil.tests_java_element import JavaElementRETest


logger = logging.getLogger("docs")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def suite():
    suite1 = unittest.TestLoader().loadTestsFromTestCase(JavaElementRETest)
    alltests = unittest.TestSuite([suite1,])
    return alltests

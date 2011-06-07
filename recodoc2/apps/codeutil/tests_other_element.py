from __future__ import unicode_literals
from django.test import TestCase
import codeutil.other_element as oe

class OtherElementTest(TestCase):
    
    def test_log_lines(self):
        snippet = '''
        Test

        This is a test
        Mike'''
        lines = snippet.split('\n')
        (log_kind, confidence) = oe.is_log_lines(lines)
        print(confidence)
        self.assertFalse(log_kind)


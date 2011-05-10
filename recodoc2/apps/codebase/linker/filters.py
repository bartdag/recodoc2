from __future__ import unicode_literals


class CustomClassFilter(object):

    def filter(self, scode_reference, code_element, log):
        return (code_element, [code_element])

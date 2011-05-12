from __future__ import unicode_literals


class FilterResult(object):

    def __init__(self, activated, code_element, potentials):
        self.activated = activated
        self.code_element = code_element
        self.potentials = potentials


class CustomClassFilter(object):

    def filter(self, scode_reference, code_element, log):
        return FilterResult(False, code_element, [code_element])

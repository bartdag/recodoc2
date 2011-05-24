from __future__ import unicode_literals
import codeutil.java_element as je
from codebase.actions import get_filters



def get_safe_element(potentials):
    if potentials is None or len(potentials) == 0:
        return None
    else:
        return potentials[0]


def get_codebase(potentials):
    if potentials is None or len(potentials) == 0:
        return None
    else:
        return potentials[0].codebase


def ref_in_snippet(code_reference):
    pass


def is_single_ref(code_reference):
    pass


class FilterResult(object):

    def __init__(self, activated, code_element, potentials):
        self.activated = activated
        self.code_element = code_element
        self.potentials = potentials


class FilterInput(object):

    def __init__(self, scode_reference, potentials, element_name, log,
            fqn_container=None, params=None):
        self.scode_reference = scode_reference
        self.potentials = potentials
        self.element_name = element_name
        self.fqn_container = fqn_container
        self.params = params
        self.log = log


class CustomClassFilter(object):

    def filter(self, filter_input):
        element_name = filter_input.element_name
        potentials = filter_input.potentials
        (simple_filters, fqn_filters) = get_filters(get_codebase(potentials))

        (simple, fqn) = je.clean_java_name(element_name) 

        # If fqn is in fqn_filters
        # And if filter agrees with ref, filter out!
        # If fqn != simple and fqn not in fqn_filters
        # Pass
        # If simple is in simple_filters
        # And if one filter agrees with ref, filter out!

        return FilterResult(False, get_safe_element(potentials), potentials)

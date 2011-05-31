from __future__ import unicode_literals
import codeutil.java_element as je
from docutil.commands_util import simple_decorator
from codebase.actions import get_filters


@simple_decorator
def empty_potentials(f):
    def newf(*args, **kargs):
        filter_input = args[1]
        potentials = filter_input.potentials
        if potentials is None or len(potentials) == 0:
            return FilterResult(False, None, [])
        else:
            return f(*args, **kargs)
    return newf


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

    def valid_filter(self, reference, afilter):
        # Check that snippets are ok
        valid = reference.snippet is None or afilter.include_snippet 

        # Check that compound references are ok
        valid = valid and (not afilter.one_ref_only or 
                (reference.parent_reference is None and 
                reference.child_references.count() == 0))

        return valid

    @empty_potentials
    def filter(self, filter_input):
        element_name = filter_input.element_name
        potentials = filter_input.potentials
        (simple_filters, fqn_filters) = get_filters(get_codebase(potentials))

        (simple, fqn) = je.clean_java_name(element_name, True) 
        result = FilterResult(False, get_safe_element(potentials), potentials)

        if fqn in fqn_filters:
            afilter = fqn_filters[fqn] 
            if self.valid_filter(filter_input.scode_reference, afilter):
                result = FilterResult(True, None, [])
        elif fqn == simple and simple in simple_filters:
            for afilter in simple_filters[simple]:
                if self.valid_filter(filter_input.scode_reference, afilter):
                    result = FilterResult(True, None, [])

        return result


class CustomClassMemberFilter(object):
    pass


class StandardLibraryFilter(object):
    pass


class ExampleFilter(object):
    pass


class ParameterNumberFilter(object):
    pass


class ParameterTypeFilter(object):
    pass


class ContextFilter(object):
    pass


class ContextReturnTypeFilter(object):
    pass


class ContextHierarchyFilter(object):
    pass


class ContextNameSimilarity(object):
    pass


class AbstractTypeFilter(object):
    pass


class StrictFilter(object):
    pass

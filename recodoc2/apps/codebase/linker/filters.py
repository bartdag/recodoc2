from __future__ import unicode_literals
import codeutil.java_element as je
import docutil.str_util as su
from docutil.commands_util import simple_decorator
from codebase.actions import get_filters


CUSTOM_FILTERS = {'CustomClassFilter', 'CustomClassMemberFilter'}


OBJECT_METHODS = {-1: set(['clone', 'equals', 'finalize', 'getClass',
                           'hashCode', 'notify', 'notifyAll', 'toString', 
                           'wait']),
                  0: set(['clone', 'finalize', 'getClass', 'hashCode',
                          'notify', 'notifyAll', 'toString', 'wait']),
                  1: set(['equals', 'wait']),
                  2: set(['wait'])
                  }


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


def get_codebase(potentials):
    if potentials is None or len(potentials) == 0:
        return None
    else:
        return potentials[0].codebase


def ref_in_snippet(code_reference):
    pass


def is_single_ref(code_reference):
    pass


def custom_filtered(filter_results):
    cfiltered = False

    for filter_result in filter_results:
        if filter_result.name in CUSTOM_FILTERS:
            cfiltered = filter_result.activated
            break

    return cfiltered


def valid_filter(reference, code_filter):
    # Check that snippets are ok
    valid = reference.snippet is None or code_filter.include_snippet 

    # Check that compound references are ok
    valid = valid and (not code_filter.one_ref_only or 
            (reference.parent_reference is None and 
            reference.child_references.count() == 0))

    return valid


def custom_filter(filter_inst, potentials, scode_reference, simple, fqn):
    (simple_filters, fqn_filters) = get_filters(get_codebase(potentials))
    simple = simple.lower()
    fqn = fqn.lower()
    result = FilterResult(filter_inst, False, potentials)

    if fqn in fqn_filters:
        afilter = fqn_filters[fqn] 
        if valid_filter(scode_reference, afilter):
            result = FilterResult(filter_inst, True, [])
    elif fqn == simple and simple in simple_filters:
        for afilter in simple_filters[simple]:
            if valid_filter(scode_reference, afilter):
                result = FilterResult(filter_inst, True, [])
                break

    return result


class FilterResult(object):

    def __init__(self, afilter, activated, potentials):
        self.name = afilter.__class__.__name__
        self.activated = activated
        self.potentials = potentials


class FilterInput(object):

    def __init__(self, scode_reference, potentials, element_name, log,
            fqn_container=None, params=None, fresults=None):
        self.scode_reference = scode_reference
        self.potentials = potentials
        self.element_name = element_name

        if fqn_container is not None:
            fqn_container = fqn_container.strip()
        self.fqn_container = fqn_container
        
        self.params = params
        self.log = log

        if fresults is None:
            fresults = []
        self.fresults = fresults
        self.fresultsd = {fresult.name: fresult for fresult in fresults}


class CustomClassFilter(object):

    @empty_potentials
    def filter(self, filter_input):
        element_name = filter_input.element_name
        potentials = filter_input.potentials
        scode_reference = filter_input.scode_reference
        (simple, fqn) = je.clean_java_name(element_name, True)
        
        result = custom_filter(self, potentials, scode_reference, simple, fqn)

        return result


class CustomClassMemberFilter(object):
    
    @empty_potentials
    def filter(self, filter_input):
        fqn_container = filter_input.fqn_container
        potentials = filter_input.potentials
        scode_reference = filter_input.scode_reference
        
        result = FilterResult(self, False, potentials)

        if fqn_container is not None and fqn_container != '':
            (simple, fqn) = je.clean_java_name(fqn_container, True)

            result = custom_filter(self, potentials, scode_reference, simple,
                    fqn)

        return result


class ObjectMethodsFilter(object):
    
    @empty_potentials
    def filter(self, filter_input):
        element_name = filter_input.element_name
        potentials = filter_input.potentials
        params = filter_input.params
        scode_reference = filter_input.scode_reference

        size = 0
        if params is not None:
            size = len(params)

        if scode_reference.snippet is not None or size > 0:
            methods = OBJECT_METHODS[size]
        else:
            methods = OBJECT_METHODS[-1]

        if element_name in methods:
            result = FilterResult(self, True, [])
        else:
            result = FilterResult(self, False, potentials)

        return result


class ExceptionFilter(object):

    @empty_potentials
    def filter(self, filter_input):
        fqn_container = filter_input.fqn_container
        potentials = filter_input.potentials

        if fqn_container is not None and \
            fqn_container.lower().endswith('exception'):
            result = FilterResult(self, True, [])
        else:
            result = FilterResult(self, False, potentials)

        return result


class ExampleFilter(object):
    pass


class ParameterNumberFilter(object):
    
    @empty_potentials
    def filter(self, filter_input):
        params = filter_input.params
        potentials = filter_input.potentials
        scode_reference = filter_input.scode_reference

        result = FilterResult(self, False, potentials)

        size = 0
        if params is not None:
            size = len(params)

        # If this is not a snippet, it might just be a method
        # name without the parameters.
        # In a snippet, the number of parameters is usually right.
        if size > 0 or scode_reference.snippet is not None:
            new_potentials = []    
            for method_element in potentials:
                if method_element.parameters_length == size:
                    new_potentials.append(method_element)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


class ParameterTypeFilter(object):

    PARAM_SIMILARITY_THRESHOLD = 0.80
    PARAM_SIZE_THRESHOLD = 0.50

    def __init__(self, simple_match=True, package_match=True):
        self.simple_match = simple_match
        self.package_match = package_match

    def _compute_match(self, actual_params, formal_params):
        matches = 0
        size = len(actual_params)

        if size != formal_params.count():
            matches = 0
        else:
            actuals = [je.clean_java_name(actual_param)[0]
                    for actual_param in actual_params]
            formals = [formal_param.type_simple_name
                    for formal_param in formal_params]
            for (actual, formal) in zip(actuals, formals):
                similarity = su.pairwise_simil(actual.lower(),
                        formal.lower())
                if similarity >= self.PARAM_SIMILARITY_THRESHOLD:
                    matches += 1
        
        # We don't want to far half-matches methods because this is too
        # fragile.
        if (float(matches) / float(size)) < self.PARAM_SIZE_THRESHOLD:
            matches = 0

        return matches

    def _compute_partial_pkg_match(self, actual_pkg, formal_pkg):
        actual_parts = actual_pkg.split('.')
        formal_parts = formal_pkg.split('.')
        matches = 0

        for (actual_part, formal_part) in zip(actual_parts, formal_parts):
            if actual_part == formal_part:
                matches += 1
            else:
                break

        matches = float(matches) / max(len(actual_parts),
                len(formal_parts))

        return matches

    def _compute_package_match(self, actual_params, formal_params):
        matches = 0
        size = len(actual_params)

        if size != formal_params.count():
            matches = 0
        else:
            actuals = [je.get_package_name(actual_param, True)
                    for actual_param in actual_params]
            formals = [je.get_package_name(formal_param.type_fqn, True)
                    for formal_param in formal_params]
            for (actual, formal) in zip(actuals, formals):
                if actual is None or formal is None:
                    continue
                elif actual == formal:
                    matches += 1
                else:
                    matches = self._compute_partial_pkg_match(actual, formal)

        return matches

    def _get_method_by_param(self, potentials, params, filter_input):
        new_potentials = []
        maximum = 1
        for method_element in potentials:
            matches = self._compute_match(params, method_element.parameters())
            if matches > maximum:
                new_potentials = [method_element]
                maximum = matches
            elif matches == maximum:
                new_potentials.append(method_element)

        return new_potentials

    def _get_method_by_param_package(self, potentials, params, filter_input):
        new_potentials = []
        maximum = 0
        for method_element in potentials:
            matches = self._compute_package_match(params,
                    method_element.parameters())
            if matches > maximum:
                new_potentials = [method_element]
                maximum = matches
            elif matches == maximum:
                new_potentials.append(method_element)

        return new_potentials

    @empty_potentials
    def filter(self, filter_input):
        params = filter_input.params
        potentials = filter_input.potentials

        result = FilterResult(self, False, potentials)

        if params is not None and len(params) > 0:
            new_potentials = []

            if self.simple_match:
                new_potentials = self._get_method_by_param(potentials, params,
                        filter_input)

            if len(new_potentials) == 0 and self.package_match:
                new_potentials = self._get_method_by_param_package(potentials,
                        params, filter_input)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


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

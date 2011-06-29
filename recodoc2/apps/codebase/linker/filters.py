from __future__ import unicode_literals
import logging
from django.conf import settings
import codeutil.java_element as je
import docutil.str_util as su
import docutil.cache_util as cu
from docutil.commands_util import simple_decorator
from codebase.models import CodeElement
import codebase.linker.context as ctx
from codebase.actions import get_filters

PREFIX_GETCONTAINER = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETCONTAINER'

CUSTOM_FILTERS = {'CustomClassFilter', 'CustomClassMemberFilter'}


OBJECT_METHODS = {-1: set(['clone', 'equals', 'finalize', 'getClass',
                           'hashCode', 'notify', 'notifyAll', 'toString',
                           'wait']),
                  0: set(['clone', 'finalize', 'getClass', 'hashCode',
                          'notify', 'notifyAll', 'toString', 'wait']),
                  1: set(['equals', 'wait']),
                  2: set(['wait'])
                  }


logger = logging.getLogger("recodoc.codebase.linker.filters")


@simple_decorator
def empty_potentials(f):
    def newf(*args, **kargs):
        filter_inst = args[0]
        filter_input = args[1]
        potentials = filter_input.potentials
        if potentials is None or len(potentials) == 0:
            return FilterResult(filter_inst, False, potentials)
        else:
            return f(*args, **kargs)
    return newf


@simple_decorator
def context_filter(f):
    def newf(*args, **kargs):
        filter_inst = args[0]
        filter_inst.__class__.is_context_filter = is_context_filter
        filter_input = args[1]
        potentials = filter_input.potentials
        context_filtered = is_context_filtered(filter_input)

        if context_filtered:
            return FilterResult(filter_inst, False, potentials)
        else:
            return f(*args, **kargs)
    return newf


def is_context_filtered(filter_input):
    fresults = filter_input.fresults
    context_filtered = False

    for fresult in fresults:
        if fresult.context_filter and fresult.activated:
            context_filtered = True
            break

    return context_filtered


def is_context_filter(self):
    return True


def get_container_value(code_element):
    containers = code_element.containers.all()
    if containers.count() == 0:
        logger.error('BIG ERROR pk={0} element={1}'.format(
            code_element.pk, code_element.human_string()))
        return None
    else:
        return containers[0]


def get_container(code_element):
    return cu.get_value(PREFIX_GETCONTAINER, code_element.pk,
            get_container_value, [code_element])


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


def valid_filter(reference, code_filter, check_member):
    # Check that members are allowed
    valid = not check_member or code_filter.include_member

    # Check that snippets are ok
    valid = valid and (reference.snippet is None or
            code_filter.include_snippet)

    # Check that compound references are ok
    valid = valid and (not code_filter.one_ref_only or
            (reference.parent_reference is None and
            reference.child_references.count() == 0))

    return valid


def custom_filter(filter_inst, potentials, scode_reference, simple, fqn,
        check_member=False):
    (simple_filters, fqn_filters) = get_filters(get_codebase(potentials))
    simple = simple.lower()
    fqn = fqn.lower()
    result = FilterResult(filter_inst, False, potentials)

    if fqn in fqn_filters:
        afilter = fqn_filters[fqn]
        if valid_filter(scode_reference, afilter, check_member):
            result = FilterResult(filter_inst, True, [])
    elif fqn == simple and simple in simple_filters:
        for afilter in simple_filters[simple]:
            if valid_filter(scode_reference, afilter, check_member):
                result = FilterResult(filter_inst, True, [])
                break

    return result


class FilterResult(object):

    def __init__(self, afilter, activated, potentials, options=''):
        try:
            self.name = afilter.get_filter_name()
        except Exception:
            self.name = afilter.__class__.__name__

        try:
            self.context_filter = afilter.is_context_filter()
        except Exception:
            self.context_filter = False

        self.activated = activated
        self.potentials = potentials
        self.options = options


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
        name = filter_input.element_name
        result = FilterResult(self, False, potentials)

        result = custom_filter(self, potentials, scode_reference, name, name,
                True)

        if not result.activated and (fqn_container is not None and
                fqn_container != ''):
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

        if (scode_reference.snippet is not None or size > 0) and\
                size in OBJECT_METHODS:
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
            actuals = [je.clean_java_name(actual_param, True, True)[0]
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

    def __init__(self, context_level, hierarchy=False, returnt=False):
        self.context_level = context_level
        self.hierarchy = hierarchy
        self.returnt = returnt

        if context_level == ctx.LOCAL:
            self.func = ctx.local_filter
        elif context_level == ctx.MIDDLE:
            self.func = ctx.mid_filter
        elif context_level == ctx.GLOBAL:
            self.func = ctx.global_filter
        elif context_level == ctx.SNIPPET:
            self.func = ctx.snippet_filter

    def get_filter_name(self):
        hierarchy = ''
        returnt = ''
        if self.hierarchy:
            hierarchy = 'Hierarchy'
        if self.returnt:
            returnt = 'Return'

        return '{0}{1}ContextFilter{2}'.format(self.context_level, returnt,
                hierarchy)

    def _get_potentials(self, potentials, context_types):
        fqns = [context_type.fqn for context_type in context_types]
        new_potentials = []

        for potential in potentials:
            container = get_container(potential)
            if container is not None and container.fqn in fqns:
                new_potentials.append(potential)

        return new_potentials

    @empty_potentials
    @context_filter
    def filter(self, filter_input):
        potentials = filter_input.potentials
        scode_reference = filter_input.scode_reference
        context_id = ctx.get_context_id(scode_reference, self.context_level)

        result = FilterResult(self, False, potentials)

        if context_id == -1:
            # This is mainly a performance optimization
            return result

        if self.returnt and not self.hierarchy:
            context_types = ctx.get_context_return_types(context_id,
                    scode_reference.source, self.func,
                    get_codebase(potentials), self.context_level)
        elif self.returnt and self.hierarchy:
            context_types = ctx.get_context_return_types_hierarchy(context_id,
                    scode_reference.source, self.func,
                    get_codebase(potentials), self.context_level)
        elif self.hierarchy:
            context_types = ctx.get_context_types_hierarchy(context_id,
                    scode_reference.source, self.func,
                    get_codebase(potentials), self.context_level)
        else:
            context_types = ctx.get_context_types(context_id,
                    scode_reference.source, self.func,
                    get_codebase(potentials), self.context_level)

        if len(context_types) > 0:
            new_potentials = self._get_potentials(potentials, context_types)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


class ImmediateContextFilter(object):

    def _get_potentials(self, potentials, fqn_container):
        new_potentials = []
        (imm_simple, imm_fqn) = je.clean_java_name(fqn_container, True, True)
        imm_simple = imm_simple.lower()
        imm_fqn = imm_fqn.lower()

        #print('DEBUG IMM: {0}, {1}'.format(imm_simple, imm_fqn))

        for potential in potentials:
            (simple, fqn) = je.clean_java_name(get_container(potential).fqn)
            #print('DEBUG POT: {0}, {1}'.format(simple, fqn))
            simple = simple.lower()
            fqn = fqn.lower()
            if imm_simple != imm_fqn:
                if fqn == imm_fqn:
                    new_potentials.append(potential)
            elif simple == imm_simple:
                new_potentials.append(potential)

        return new_potentials

    @empty_potentials
    @context_filter
    def filter(self, filter_input):
        fqn_container = filter_input.fqn_container
        potentials = filter_input.potentials

        result = FilterResult(self, False, potentials)

        if fqn_container is not None and \
                fqn_container != je.UNKNOWN_CONTAINER:

            #print('DEBUG FQN: {0}'.format(fqn_container))
            new_potentials = self._get_potentials(potentials, fqn_container)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


class ImmediateContextHierarchyFilter(object):

    def _get_potentials(self, potentials, fqn_container):
        new_potentials = []
        (imm_simple, imm_fqn) = je.clean_java_name(fqn_container, True, True)
        imm_simple = imm_simple.lower()
        imm_fqn = imm_fqn.lower()

        for potential in potentials:
            container = get_container(potential)
            if container is None:
                continue
            hierarchy = ctx.get_hierarchy(container)
            for element in hierarchy:
                (simple, fqn) = je.clean_java_name(element.fqn)
                simple = simple.lower()
                fqn = fqn.lower()
                if imm_simple != imm_fqn:
                    if fqn == imm_fqn:
                        new_potentials.append(potential)
                        break
                elif simple == imm_simple:
                    new_potentials.append(potential)
                    break

        return new_potentials

    @empty_potentials
    @context_filter
    def filter(self, filter_input):
        fqn_container = filter_input.fqn_container
        potentials = filter_input.potentials

        result = FilterResult(self, False, potentials)

        if fqn_container is not None and \
                fqn_container != je.UNKNOWN_CONTAINER:
            new_potentials = self._get_potentials(potentials, fqn_container)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


class ContextNameSimilarityFilter(object):

    DIFFERENCE_THRESHOLD = 0.2

    PAIRWISE_THRESHOLD = 0.66

    HIGH_SIMILARITY = 0.95

    def _get_common_token_ratio(self, container_tokens, potential_tokens):
        max_token = max(len(container_tokens), len(potential_tokens))
        count = 0
        for token in container_tokens:
            if token in potential_tokens:
                count += 1

        return float(count) / float(max_token)

    def _get_potentials_by_similarity(self, potentials, fqn_container):
        new_potentials = []
        max_similarity = 0.0

        (container_simple, _) = je.clean_java_name(fqn_container, True, True)
        container_tokens = [token.lower()
                for token in su.tokenize(container_simple)]
        container_simple_lower = container_simple.lower()
        similarities = []

        for potential in potentials:
            (simple, _) = je.clean_java_name(get_container(potential).fqn)
            potential_tokens = [token.lower()
                for token in su.tokenize(simple)]
            simple_lower = simple.lower()
            common_token = self._get_common_token_ratio(container_tokens,
                    potential_tokens)
            psimilarity = su.pairwise_simil(container_simple_lower,
                    simple_lower)

            # This is the minimum required by this filter:
            if common_token == 0.0 or psimilarity < self.PAIRWISE_THRESHOLD:
                continue

            similarity = max(common_token, psimilarity)
            if similarity > max_similarity:
                max_similarity = similarity

            similarities.append((potential, similarity))

        # Only keep the elements that match the threshold
        # Or accept elements that are fuzzily near the max_similarity
        if max_similarity < self.HIGH_SIMILARITY:
            max_similarity = max_similarity - self.DIFFERENCE_THRESHOLD

        for (potential, similarity) in similarities:
            if similarity >= max_similarity:
                new_potentials.append(potential)

        return new_potentials

    @empty_potentials
    @context_filter
    def filter(self, filter_input):
        fqn_container = filter_input.fqn_container
        potentials = filter_input.potentials

        result = FilterResult(self, False, potentials)

        if (fqn_container is not None and
                fqn_container != je.UNKNOWN_CONTAINER):
            new_potentials = self._get_potentials_by_similarity(potentials,
                    fqn_container)

            if len(new_potentials) > 0:
                result = FilterResult(self, True, new_potentials)

        return result


class AbstractTypeFilter(object):

    def _get_potentials(self, potentials):
        new_potentials = []

        for potential in potentials:
            container = get_container(potential)

            if container is None:
                size = 0
            else:
                descendants = ctx.get_descendants(container)
                size = len(descendants)
            new_potentials.append((potential, size))

        new_potentials.sort(key=lambda v: v[1], reverse=True)

        return [potential[0] for potential in new_potentials]

    @empty_potentials
    def filter(self, filter_input):
        potentials = filter_input.potentials

        result = FilterResult(self, False, potentials)

        new_potentials = self._get_potentials(potentials)

        # Here we check for more than one potential, otherwise,
        # There was no sorting!
        if len(new_potentials) > 1:
            result = FilterResult(self, True, new_potentials)

        return result


class StrictFilter(object):
    PARAM_THRESHOLD = 3
    TOKEN_THRESHOLD = 3

    def _get_tokens(self, method_name):
        getter_setter = method_name.startswith('get') or \
            method_name.startswith('set')

        token_size = len(su.tokenize(method_name))

        if getter_setter:
            token_size -= 1

        return token_size

    @empty_potentials
    def filter(self, filter_input):
        element_name = filter_input.element_name
        potentials = filter_input.potentials
        new_potentials = potentials
        params = filter_input.params
        size = len(potentials)
        options = ''
        context_filtered = is_context_filtered(filter_input)
        strict_filtered = True

        if context_filtered:
            options = 'context'
            strict_filtered = False
        elif size == 1 and params is not None and \
                len(params) >= self.PARAM_THRESHOLD:
            options = 'params'
            strict_filtered = False
        elif size == 1 and \
                self._get_tokens(element_name) >= self.TOKEN_THRESHOLD:
            options = 'token'
            strict_filtered = False

        if strict_filtered:
            new_potentials = []

        result = FilterResult(self, strict_filtered, new_potentials, options)

        return result

from __future__ import unicode_literals
import logging
from django.conf import settings
import docutil.cache_util as cu
from codebase.models import SingleCodeReference


PREFIX_GETANCESTORS = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETANCESTORS'

PREFIX_GETDESCENDANTS = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETDESCENDANTS'

PREFIX_GETHIERARCHY = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETHIERARCHY'

PREFIX_GETCONTEXT = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETCONTEXT'

HIERARCHY = 'hier'

IMMEDIATE = 'imm'

SNIPPET = 'snip'

LOCAL = 'loc'

RETURN = 'ret'

MIDDLE = 'mid'

GLOBAL = 'glob'

logger = logging.getLogger("recodoc.codebase.linker.context")


def add_ancestors(code_element, ancestors, pk_set):
    if code_element is None:
        return

    for parent in code_element.parents.all():
        if parent.kind.is_type and parent.pk not in pk_set:
            ancestors.add(parent)
            pk_set.add(parent.pk)
            add_ancestors(parent, ancestors, pk_set)


def get_ancestors_value(code_element):
    pk_set = set()
    ancestors = []
    add_ancestors(code_element, ancestors, pk_set)
    return ancestors


def add_descendants(code_element, descendants, pk_set):
    if code_element is None:
        return

    for child in code_element.children.all():
        if child.kind.is_type and child.pk not in pk_set:
            descendants.add(child)
            pk_set.add(child.pk)
            add_descendants(child, descendants, pk_set)


def get_descendants_value(code_element):
    pk_set = set()
    descendants = []
    add_descendants(code_element, descendants, pk_set)


def get_context_return_types_hier_value(context_id, soruce, codebase):
    pass


def get_context_return_types_value(context_id, source, codebase):
    pass


def get_context_types_hier_value(context_id, source, filter_func, codebase):
    pass


def get_context_types_value(context_id, source, filter_func, codebase):
    pass


def get_hierarchy_value(code_element):
    hierarchy = [code_element]
    hierarchy.extend(get_ancestors(code_element))
    hierarchy.extend(get_descendants(code_element))
    return hierarchy


def get_ancestors(code_element):
    return cu.get_value(PREFIX_GETANCESTORS, code_element.pk,
            get_ancestors_value, [code_element])


def get_descendants(code_element):
    return cu.get_value(PREFIX_GETDESCENDANTS, code_element.pk,
            get_descendants_value, [code_element])


def get_context_return_types_hierarchy(context_id, source, codebase):
    return cu.get_value(PREFIX_GETCONTEXT + HIERARCHY + source + RETURN,
            context_id, get_context_return_types_hier_value, [context_id,
                source, codebase])


def get_context_return_types(context_id, source, codebase):
    return cu.get_value(PREFIX_GETCONTEXT + source + RETURN, context_id,
            get_context_return_types_value, [context_id, source, codebase])


def get_context_types_hierarchy(context_id, source, filter_func, codebase,
        context_level):
    return cu.get_value(PREFIX_GETCONTEXT + HIERARCHY + source + context_level,
            context_id, get_context_types_hier_value, [context_id, source,
                filter_func, codebase])


def get_context_types(context_id, source, filter_func, codebase,
        context_level):
    return cu.get_value(PREFIX_GETCONTEXT + source + context_level,
            context_id, get_context_types_value, [context_id, source,
                filter_func, codebase])


def get_hierarchy(code_element):
    return cu.get_value(PREFIX_GETHIERARCHY, code_element.pk,
            get_hierarchy_value, [code_element])

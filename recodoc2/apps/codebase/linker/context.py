from __future__ import unicode_literals
import logging
from django.conf import settings
import docutil.cache_util as cu
from codebase.models import CodeElementLink, CodeElement


PREFIX_GETANCESTORS = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETANCESTORS'

PREFIX_GETDESCENDANTS = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETDESCENDANTS'

PREFIX_GETHIERARCHY = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETHIERARCHY'

PREFIX_GETCONTEXT = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'GETCONTEXT'

HIERARCHY = 'hier'

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
            ancestors.append(parent)
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
            descendants.append(child)
            pk_set.add(child.pk)
            add_descendants(child, descendants, pk_set)


def get_descendants_value(code_element):
    pk_set = set()
    descendants = []
    add_descendants(code_element, descendants, pk_set)
    return descendants


def get_context_return_types_hier_value(context_id, source, filter_func,
        codebase, context_level):
    return_types = get_context_return_types(context_id, source, filter_func,
            codebase, context_level)

    return_types_hier = []
    pk_set = set()

    for code_element in return_types:
        hierarchy = get_hierarchy(code_element)
        for code_element_h in hierarchy:
            if code_element_h.pk not in pk_set:
                return_types_hier.append(code_element_h)
                pk_set.add(code_element_h.pk)

    return return_types_hier


def get_context_return_types_value(context_id, source, filter_func, codebase):
    query = CodeElementLink.objects.\
            filter(code_element__kind__kind='method').\
            filter(index=0).\
            filter(code_element__codebase=codebase).\
            filter(code_reference__source=source)
    #print(query.count())
    query = filter_func(query, context_id)
    #print(query.count())

    return_types = []
    fqn_set = set()

    for link in query.all():
        code_element = link.code_element.methodelement
        return_fqn = code_element.return_fqn
        if return_fqn not in fqn_set:
            fqn_set.add(return_fqn)
            try:
                return_element = CodeElement.objects.\
                        filter(codebase=codebase).\
                        filter(fqn=return_fqn).all()[0]
                return_types.append(return_element)
            except Exception:
                pass

    return return_types


def get_context_types_hier_value(context_id, source, filter_func, codebase,
        context_level):
    context_types = get_context_types(context_id, source, filter_func,
            codebase, context_level)

    context_types_hier = []
    pk_set = set()
    for code_element in context_types:
        hierarchy = get_hierarchy(code_element)
        for code_element_h in hierarchy:
            if code_element_h.pk not in pk_set:
                context_types_hier.append(code_element_h)
                pk_set.add(code_element_h.pk)

    return context_types_hier


def get_context_types_value(context_id, source, filter_func, codebase):
    #print('In context types value')
    query = CodeElementLink.objects.filter(code_element__kind__is_type=True).\
            filter(index=0).\
            filter(code_element__codebase=codebase).\
            filter(code_reference__source=source)
    #print(query.count())
    query = filter_func(query, context_id)
    #print(query.count())

    context_types = []
    pk_set = set()

    for link in query.all():
        code_element = link.code_element
        if code_element.pk not in pk_set:
            context_types.append(code_element)
            pk_set.add(code_element.pk)

    return context_types


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


def get_context_return_types_hierarchy(context_id, source, filter_func,
        codebase, context_level):
    return get_context_return_types_hier_value(context_id, source, filter_func,
            codebase, context_level)
    #return cu.get_value(PREFIX_GETCONTEXT + HIERARCHY + source + context_level
            #+ RETURN, context_id, get_context_return_types_hier_value,
            #[context_id, source, filter_func, codebase, context_level])


def get_context_return_types(context_id, source, filter_func, codebase,
        context_level):
    return get_context_return_types_value(context_id, source, filter_func,
            codebase)
    #return cu.get_value(PREFIX_GETCONTEXT + source + context_level + RETURN,
            #context_id, get_context_return_types_value, [context_id, source,
                #filter_func, codebase])


def get_context_types_hierarchy(context_id, source, filter_func, codebase,
        context_level):
    return cu.get_value(PREFIX_GETCONTEXT + HIERARCHY + source + context_level,
            context_id, get_context_types_hier_value, [context_id, source,
                filter_func, codebase, context_level])


def get_context_types(context_id, source, filter_func, codebase,
        context_level):
    return cu.get_value(PREFIX_GETCONTEXT + source + context_level,
            context_id, get_context_types_value, [context_id, source,
                filter_func, codebase])


def get_hierarchy(code_element):
    return cu.get_value(PREFIX_GETHIERARCHY, code_element.pk,
            get_hierarchy_value, [code_element])


def get_context_id(scode_reference, context_level):
    context_id = -1

    if context_level == LOCAL:
        context_id = scode_reference.local_object_id
    elif context_level == MIDDLE:
        context_id = scode_reference.mid_object_id
    elif context_level == GLOBAL:
        context_id = scode_reference.global_object_id
    elif context_level == SNIPPET:
        if scode_reference.snippet is not None:
            context_id = scode_reference.snippet.pk

    if context_id is None:
        context_id = -1

    return context_id


def local_filter(query, context_id):
    return query.filter(code_reference__local_object_id=context_id)


def mid_filter(query, context_id):
    return query.filter(code_reference__mid_object_id=context_id)


def global_filter(query, context_id):
    return query.filter(code_reference__global_object_id=context_id)


def snippet_filter(query, context_id):
    return query.filter(code_reference__snippet__pk=context_id)

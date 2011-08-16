from __future__ import unicode_literals
import logging
from collections import defaultdict
from django.conf import settings
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import call_gc, queryset_iterator
import docutil.str_util as su
import docutil.cache_util as cu
import codeutil.java_element as je
import codebase.linker.context as ctx
import codebase.linker.generic_linker as gl
import codebase.linker.filters as filters
from codebase.models import CodeElementKind, ReleaseLinkSet, MethodElement,\
        MethodInfo, FieldElement

### PPA CONSTANTS ###
HANDLE_SEPARATOR = ":"
UNKNOWN_PACKAGE = 'UNKNOWNP'
SNIPPET_PACKAGE = 'zzzsnippet'
UNKNOWN_TYPE = 'UNKNOWNP.UNKNOWN'
SNIPPET_TYPE = 'zzzsnippet.ZZZSnippet'


### CACHE PREFIXES ###
PREFIX_UNKNOWN = settings.CACHE_MIDDLEWARE_KEY_PREFIX + 'UNKNOWN'
PREFIX_ANNOTATION_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaannlinker'
PREFIX_ENUMERATION_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaenumlinker'
PREFIX_CLASS_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaclslinker'
PREFIX_METHOD_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javamethodlinker'
PREFIX_ANN_FIELD_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaannfieldlinker'
PREFIX_ENUM_VAL_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaenumvallinker'
PREFIX_FIELD_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javafieldlinker'
PREFIX_CLASS_POST_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javaclspostlinker'
PREFIX_GENERIC_LINKER = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
    'javagenlinker'

UNKNOWN_KEY = 'UNKNOWN'


### QUERY CONSTANTS FOR FILTERS ###
SIMPLE = 'SIMPLE'
FQN = 'FQN'
EXACT = 'EXACT'
IEXACT = 'IEXACT'


# THRESHOLDS
FQN_SIMILARITY_THRESHOLD = 0.80


logger = logging.getLogger("recodoc.codebase.linker")


def reclassify_java(code_element, scode_reference):
    reclassified = False

    if scode_reference.snippet is not None or code_element is not None:
        # We assume that references from snippet are always correctly
        # classified. References that were linked to a code element
        # do not need to be reclassified.
        return reclassified

    automatic_reclass = set(['method', 'field', 'annotation field',
        'enumeration value', 'annotation', 'enumeration'])
    unknown_kind = cu.get_value(PREFIX_UNKNOWN, UNKNOWN_KEY,
            gl.get_unknown_kind, None)

    if scode_reference.kind_hint.kind in automatic_reclass:
        scode_reference.kind_hint = unknown_kind
        reclassified = True
    elif scode_reference.child_references.count() == 0:
        # This was a single class reference, not mixed with a field or a
        # method (in which case, the field/method will be reclassified if
        # there is a need to). Maybe it was a reference to a method or a
        # field. The simple name will be compared with all code elements
        scode_reference.kind_hint = unknown_kind
        reclassified = True

    if reclassified:
        scode_reference.save()

    return reclassified


def find_package(code_element):
    while code_element is not None and\
            code_element.kind.kind != 'package':
        code_element = code_element.containers.all()[0]

    if code_element is not None:
        return code_element.fqn
    else:
        return None


def get_package_freq(local_ctx_id, source, prelease):
    linksets = ReleaseLinkSet.objects\
            .filter(code_reference__local_object_id=local_ctx_id)\
            .filter(code_reference__source=source)\
            .filter(project_release=prelease).all()

    packages = defaultdict(int)

    for linkset in linksets:
        if linkset.links.count() == 1:
            package_name = find_package(linkset.first_link.code_element)
            if package_name is not None:
                packages[package_name] += 1

    package_freq = [(k, packages[k]) for k in packages]
    package_freq.sort(key=lambda v: v[1], reverse=True)

    return package_freq


class JavaClassLinker(gl.DefaultLinker):
    name = 'javaclass'

    def __init__(self, project, prelease, codebase, source, srelease=None,
            filtered_ids=None):
        super(JavaClassLinker, self).__init__(project, prelease, codebase,
                source, srelease, filtered_ids)
        self.ann_kind = CodeElementKind.objects.get(kind='annotation')
        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.enum_kind = CodeElementKind.objects.get(kind='enumeration')
        self.class_filters = [
                filters.CustomClassFilter(),
                filters.FQNCaseFilter(),
                ]

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):

        # Annotations
        ann_refs = self._get_query(self.ann_kind, local_object_id)
        acount = ann_refs.count()
        progress_monitor.info('Annotation count: {0}'.format(acount))
        try:
            self._link_annotations(queryset_iterator(ann_refs), acount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing annotations.')
        call_gc()

        # Enumerations
        enum_refs = self._get_query(self.enum_kind, local_object_id)
        ecount = enum_refs.count()
        progress_monitor.info('Enumeration count: {0}'.format(ecount))
        try:
            self._link_enumerations(queryset_iterator(enum_refs), ecount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing enumerations.')
        call_gc()

        # All types (including classes!)
        class_refs = self._get_query(self.class_kind, local_object_id)
        ccount = class_refs.count()
        progress_monitor.info('Class count: {0}'.format(ccount))
        try:
            self._link_classes(queryset_iterator(class_refs), ccount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing classes.')
        call_gc()

    def _link_annotations(self, ann_refs, acount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing annotations', acount)
        log = gl.LinkerLog(self, self.ann_kind.kind)

        for scode_reference in ann_refs:
            #if scode_reference.declaration:
                #progress_monitor.work('Skipped declaration', 1)
                #continue
            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue

            (simple, fqn) = je.get_annotation_name(scode_reference.content,
                    scode_reference.snippet is not None)

            if simple is not None:
                prefix = '{0}{1}{2}'.format(PREFIX_ANNOTATION_LINKER, EXACT,
                    cu.get_codebase_key(self.codebase))
                code_elements = cu.get_value(
                        prefix,
                        simple,
                        gl.get_type_code_elements,
                        [simple, self.codebase, self.ann_kind])

                (code_element, potentials) = self.get_code_element(
                        scode_reference, code_elements, simple, fqn, log)
                count += gl.save_link(scode_reference, code_element,
                        potentials, self)

                if not log.custom_filtered:
                    reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed annotation', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} annotations'.format(count))

    def _link_enumerations(self, enum_refs, ecount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing enumerations', ecount)
        log = gl.LinkerLog(self, self.enum_kind.kind)

        for scode_reference in enum_refs:
            #if scode_reference.declaration:
                #progress_monitor.work('Skipped declaration', 1)
                #continue

            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue

            (simple, fqn) = je.get_class_name(scode_reference.content,
                    scode_reference.snippet is not None)

            if simple is not None:
                prefix = '{0}{1}{2}'.format(PREFIX_ENUMERATION_LINKER, EXACT,
                    cu.get_codebase_key(self.codebase))
                code_elements = cu.get_value(
                        prefix,
                        simple,
                        gl.get_type_code_elements,
                        [simple, self.codebase, self.enum_kind])

                (code_element, potentials) = self.get_code_element(
                        scode_reference, code_elements, simple, fqn, log)
                count += gl.save_link(scode_reference, code_element,
                        potentials, self)

                if not log.custom_filtered:
                    reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed enumeration', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} enumerations'.format(count))

    def _link_classes(self, class_refs, ccount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing classes', ccount)
        log = gl.LinkerLog(self, self.class_kind.kind)

        for scode_reference in class_refs:
            #if scode_reference.declaration:
                #progress_monitor.work('Skipped declaration', 1)
                #continue

            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue

            (simple, fqn) = je.get_class_name(scode_reference.content,
                    scode_reference.snippet is not None)
            case_insensitive = scode_reference.snippet == None and\
                    self.source != 'd'

            if case_insensitive:
                exact = False
                exact_prefix = IEXACT
            else:
                exact = True
                exact_prefix = EXACT

            if simple is not None:
                prefix = '{0}{1}{2}'.format(PREFIX_CLASS_LINKER, exact_prefix,
                    cu.get_codebase_key(self.codebase))
                code_elements = []
                code_elements.extend(cu.get_value(
                        prefix,
                        simple,
                        gl.get_type_code_elements,
                        [simple, self.codebase, self.class_kind, exact]))

                prefix = '{0}{1}{2}'.format(PREFIX_ANNOTATION_LINKER,
                        exact_prefix, cu.get_codebase_key(self.codebase))
                code_elements.extend(cu.get_value(
                        prefix,
                        simple,
                        gl.get_type_code_elements,
                        [simple, self.codebase, self.ann_kind, exact]))

                prefix = '{0}{1}{2}'.format(PREFIX_ENUMERATION_LINKER,
                        exact_prefix, cu.get_codebase_key(self.codebase))
                code_elements.extend(cu.get_value(
                        prefix,
                        simple,
                        gl.get_type_code_elements,
                        [simple, self.codebase, self.enum_kind, exact]))

                (code_element, potentials) = self.get_code_element(
                        scode_reference, code_elements, simple, fqn, log,
                        not exact)
                count += gl.save_link(scode_reference, code_element,
                        potentials, self)

                if not log.custom_filtered:
                    reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed class', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} classes'.format(count))

    def get_code_element(self, scode_reference, code_elements, simple, fqn,
            log, insensitive=False):
        log.reset_variables()
        return_code_element = None
        potentials = code_elements
        if code_elements is None:
            size = 0
        else:
            size = len(code_elements)

        # DEBUG
        #print('DEBUG for {0}'.format(scode_reference.content))
        #for code_element in code_elements:
            #print(code_element.fqn)

        if size > 0:
            if size == 1:
                # There is only one code element.
                return_code_element = code_elements[0]
                potentials = [return_code_element]
                log.one = True
            elif fqn == simple \
                    or fqn.find(UNKNOWN_PACKAGE) != -1 \
                    or fqn.find(SNIPPET_PACKAGE) != -1:
                # Many elements and fqn is unknown
                return_code_element = code_elements[0]
                log.arbitrary = True
            elif insensitive:
                # Do an insensitive comparison on the fqn.
                fqn_lower = fqn.lower()
                sims = [su.pairwise_simil(fqn_lower, code_element.fqn.lower())
                        for code_element in code_elements]
                max_sim = max(sims)
                index = sims.index(max_sim)
                return_code_element = code_elements[index]
                del(potentials[index])
                potentials.insert(0, return_code_element)
                if max_sim >= FQN_SIMILARITY_THRESHOLD:
                    potentials = [return_code_element]
                log.insensitive = True
            else:
                # Do a case sensitive comparison on the fqn
                sims = [su.pairwise_simil(fqn, code_element.fqn)
                        for code_element in code_elements]
                max_sim = max(sims)
                index = sims.index(max_sim)
                return_code_element = code_elements[index]
                del(potentials[index])
                potentials.insert(0, return_code_element)
                if max_sim >= FQN_SIMILARITY_THRESHOLD:
                    potentials = [return_code_element]
                log.sensitive = True

        filter_results = []
        for afilter in self.class_filters:
            finput = filters.FilterInput(scode_reference, potentials,
                    fqn, log, None, None, filter_results)
            result = afilter.filter(finput)
            potentials = result.potentials
            filter_results.append(result)

        potentials_size = len(potentials)
        if potentials_size > 0:
            return_code_element = potentials[0]
        else:
            return_code_element = None

        log.custom_filtered = filters.custom_filtered(filter_results)

        # Logging
        log.log_type(simple, fqn, scode_reference, return_code_element,
                potentials, size, filter_results)

        return (return_code_element, potentials)


class JavaPostClassLinker(gl.DefaultLinker):
    name = 'javapostclass'

    def __init__(self, project, prelease, codebase, source, srelease=None,
            filtered_ids=None):
        super(JavaPostClassLinker, self).__init__(project, prelease, codebase,
                source, srelease, filtered_ids)

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):

        # Get link to filter.
        linksets = ReleaseLinkSet.objects\
                .filter(project_release=self.prelease)\
                .filter(first_link__code_element__kind__is_type=True)

        count = linksets.count()
        progress_monitor.start('Post-Processing Classes', count)
        log = gl.LinkerLog(self, 'type')

        for linkset in queryset_iterator(linksets):
            log.reset_variables()
            scode_reference = linkset.code_reference

            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue

            lcount = linkset.links.count()
            if lcount <= 1:
                log.log_type('', '', scode_reference,
                        linkset.first_link.code_element,
                        [linkset.first_link], lcount, [], 'onlyone')
                progress_monitor.work('Skipped a linkset.', 1)
                continue

            local_ctx_id = scode_reference.local_object_id
            source = scode_reference.source
            prefix = '{0}{1}{2}'.format(PREFIX_CLASS_POST_LINKER,
                cu.get_codebase_key(self.codebase), source)
            package_freq = cu.get_value(
                    prefix,
                    local_ctx_id,
                    get_package_freq,
                    [local_ctx_id, source, self.prelease])

            # Find package with highest frequency
            code_element = self._find_package_by_freq(linkset, package_freq)
            rationale = 'highest_frequency'

            # Heuristic
            if code_element is None:
                code_element = self._find_package_by_depth(linkset)
                rationale = 'heuristic_depth'

            # Update links
            if code_element is not None:
                linkset.first_link.code_element = code_element
                linkset.first_link.linker_name = self.name
                linkset.first_link.rationale = rationale
                linkset.first_link.save()
                for link in linkset.links.all()[1:]:
                    link.delete()
                log.log_type('', '', scode_reference,
                        linkset.first_link.code_element,
                        [linkset.first_link], lcount, [], rationale)
                progress_monitor.info('FOUND Best Package {0} because {1}'
                        .format(code_element.fqn, rationale))
            else:
                potentials =\
                    [link.code_element for link in linkset.links.all()]
                log.log_type('', '', scode_reference,
                        linkset.first_link.code_element,
                        potentials, lcount, 'nomatch')

            progress_monitor.work('Processed a linkset.', 1)

        progress_monitor.done()

    def _find_package_by_depth(self, linkset):
        best_depth = -1
        best_package_name = ''
        best_element = None

        for link in linkset.links.all():
            package = find_package(link.code_element)
            if package is not None:
                depth = len(package.split('.'))
                if best_depth == -1 or depth < best_depth:
                    best_depth = depth
                    best_package_name = package
                    best_element = link.code_element
                elif depth == best_depth:
                    # Same depth, alphanumeric comparison
                    if package < best_package_name:
                        best_package_name = package
                        best_element = link.code_element

        return best_element

    def _find_package_by_freq(self, linkset, package_freq):
        package_names = [p[0] for p in package_freq]
        size = len(package_freq)
        # Best Index = index of package with highest frequency.
        # List of packages is sorted by decreasing frequency.
        # index = 0 == highest frequency
        best_index = size
        best_element = None

        for link in linkset.links.all():
            package = find_package(link.code_element)
            if package is not None:
                try:
                    index = package_names.index(package)
                    if index < best_index:
                        if index == size - 1 or best_index == size:
                            best_index = index
                            best_element = link.code_element
                        # Otherwise, frequency is equivalent and it's not good!
                        elif package_freq[index][1] >\
                                package_freq[best_index][1]:
                            best_index = index
                            best_element = link.code_element
                        # Compare depth!
                        else:
                            depth_best =\
                                len(package_names[best_index].split('.'))
                            depth_index =\
                                len(package_names[index].split('.'))

                            # At equal frequency, compare depth
                            if depth_best < depth_index:
                                continue
                            elif depth_index < depth_best:
                                best_index = index
                                best_element = link.code_element
                            else:
                                best_index = size
                                best_element = None
                except Exception:
                    pass

        return best_element


class JavaMethodLinker(gl.DefaultLinker):
    name = 'javamethod'

    def __init__(self, project, prelease, codebase, source, srelease=None,
            filtered_ids=None):
        super(JavaMethodLinker, self).__init__(project, prelease, codebase,
                source, srelease, filtered_ids)
        self.method_kind = CodeElementKind.objects.get(kind='method')
        self.method_filters = [
                filters.ObjectMethodsFilter(),
                filters.ExceptionFilter(),
                filters.FQNCaseFilter(),
                filters.CustomClassMemberFilter(),
                filters.ParameterNumberFilter(),
                filters.ParameterTypeFilter(),
                filters.ImmediateContextFilter(),
                filters.ImmediateContextHierarchyFilter(),
                filters.ContextFilter(ctx.SNIPPET),
                filters.ContextFilter(ctx.SNIPPET, True),
                filters.ContextFilter(ctx.SNIPPET, False, True),
                filters.ContextFilter(ctx.SNIPPET, True, True),
                filters.ContextFilter(ctx.LOCAL),
                filters.ContextFilter(ctx.LOCAL, True),
                filters.ContextFilter(ctx.LOCAL, False, True),
                filters.ContextFilter(ctx.LOCAL, True, True),
                filters.ContextFilter(ctx.MIDDLE),
                filters.ContextFilter(ctx.MIDDLE, True),
                filters.ContextFilter(ctx.GLOBAL),
                filters.ContextFilter(ctx.GLOBAL, True),
                filters.ContextNameSimilarityFilter(),
                filters.UniqueHierarchyFilter(),
                filters.AbstractTypeFilter(),
                filters.StrictFilter(),
                ]

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):

        method_refs = self._get_query(self.method_kind, local_object_id)
        mcount = method_refs.count()
        progress_monitor.info('Method count: {0}'.format(mcount))
        try:
            # Here, use an iterator instead of the query set because we really
            # want to keep the ordering by index...
            self._link_methods(method_refs.iterator(), mcount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing methods')

        call_gc()

    def _link_methods(self, method_refs, mcount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing methods', mcount)
        log = gl.LinkerLog(self, self.method_kind.kind)

        for scode_reference in method_refs:
            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue
            method_info = self._get_method_info(scode_reference)
            code_elements = self._get_method_elements(method_info)

            (code_element, potentials) = self.get_code_element(
                    scode_reference, code_elements, method_info, log)
            count += gl.save_link(scode_reference, code_element, potentials,
                    self)

            if not log.custom_filtered:
                reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed method', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} methods'.format(count))

    def _get_method_elements(self, method_info):
            prefix = '{0}{1}'.format(PREFIX_METHOD_LINKER,
                cu.get_codebase_key(self.codebase))
            method_name = method_info.method_name
            code_elements = cu.get_value(
                    prefix,
                    method_name,
                    gl.get_type_code_elements,
                    [method_name, self.codebase, self.method_kind, True,
                        MethodElement])

            return code_elements

    def _get_method_info(self, scode_reference, skip_complex_search=False):
        method_name = fqn_container = nb_params = type_params = None

        if scode_reference.snippet != None:
            parts = scode_reference.content.split(HANDLE_SEPARATOR)
            (method_name, fqn_container, nb_params, type_params) = \
                    self._get_method_info_snippet(parts)
        else:
            content = scode_reference.content
            match1 = je.CALL_CHAIN_RE.search(content)
            match2 = je.METHOD_DECLARATION_RE.search(content)
            match3 = je.METHOD_SIGNATURE_RE.search(content)
            match4 = je.SIMPLE_CALL_RE.search(content)

            if match1 and not skip_complex_search:
                (method_name, fqn_container) = self._get_method_header(match1)
                eindex = content.index(')')
                sindex = content.index('(')
                params_text = content[sindex + 1:eindex]

                if len(params_text) == 0:
                    # This means that there was no parameter, so no ','
                    nb_params = 0
                else:
                    params = params_text.split(',')
                    nb_params = len(params)
                    type_params = [param.strip() for param in params]

            elif match2 and not skip_complex_search:
                method_name = match2.group('method_name')
                eindex = content.index(')')
                sindex = content.index('(')
                params_text = content[sindex + 1:eindex]

                if len(params_text) == 0:
                    # This means that there was no parameter, so no ','
                    nb_params = 0
                else:
                    params = params_text.split(',')
                    nb_params = len(params)
                    type_params = [param.strip() for param in params]
            elif match3 and not skip_complex_search:
                (method_name, fqn_container) = self._get_method_header(match3)
                (nb_params, type_params) = self._get_method_params(match3)
            elif match4 and not skip_complex_search:
                (method_name, fqn_container) = self._get_method_header(match4)
                (nb_params, type_params) = self._get_method_params(match4)
            else:
                if len(content.strip()) > 0:
                    method_name = je.get_clean_name(content)

            # Convert literals
            if type_params is not None:
                for i, type_param in enumerate(type_params):
                    if type_param is not None:
                        type_param = type_param.strip()
                        atype = je.find_type(type_param)
                        if atype is not None:
                            type_params[i] = atype

        if type_params is not None:
            type_params = \
                    [su.safe_strip(type_param) for type_param in type_params]

        return MethodInfo(su.safe_strip(method_name),
                su.safe_strip(fqn_container), nb_params, type_params)

    def _get_method_info_snippet(self, parts):
        method_name = fqn_container = nb_params = type_params = None

        try:
            method_name = parts[2]
            fqn_container = parts[1]
            type_params = parts[3:]
            nb_params = len(type_params)
        except Exception:
            logger.exception('An exception has occurred')

        return (method_name, fqn_container, nb_params, type_params)

    def _get_method_header(self, match):
        fqn_container = None
        groupdict = match.groupdict()
        method_name = groupdict['method_name']
        if 'target' in groupdict:
            target = groupdict['target']
            if target is not None and len(target.strip()) > 0:
                fqn_container = je.clean_java_name(groupdict['target'])[1]
        return (method_name, fqn_container)

    def _get_method_params(self, match):
        nb_params = type_params = None
        if match.group(3) == None:
            # First argument
            nb_params = 0
        elif match.group(4) == None:
            # Other arguments
            nb_params = 1
            type_params = [match.group(3)]
        else:
            text = match.string[match.end(2):]
            eindex = text.index(')')
            sindex = text.index('(')
            params_text = text[sindex + 1:eindex]
            if len(params_text) == 0:
                # This means that there was no parameter, so no ','
                nb_params = 0
            else:
                params = params_text.split(',')
                nb_params = len(params)
                type_params = [param.strip() for param in params]

        return (nb_params, type_params)

    def get_code_element(self, scode_reference, code_elements, method_info,
            log):
        log.reset_variables()
        return_code_element = None
        if code_elements is None:
            code_elements = []
        potentials = list(code_elements)
        size = len(code_elements)

        #print('DEBUG FOR {0}:{1}'.format(scode_reference.pk,
            #scode_reference.content))
        #for code_element in code_elements:
            #print(code_element.fqn)

        filter_results = []

        method_name = method_info.method_name
        params = method_info.type_params
        fqn_container = method_info.fqn_container

        for afilter in self.method_filters:
            finput = filters.FilterInput(scode_reference, potentials,
                    method_name, log, fqn_container, params, filter_results)
            result = afilter.filter(finput)
            potentials = result.potentials
            filter_results.append(result)

        log.custom_filtered = filters.custom_filtered(filter_results)

        potentials_size = len(potentials)
        if potentials_size == 1:
            return_code_element = potentials[0]
        elif potentials_size > 1:
            return_code_element = potentials[0]
            log.arbitrary = True

        # Logging
        log.log_method(method_info, scode_reference, return_code_element,
                potentials, size, filter_results, code_elements)
        return (return_code_element, potentials)


class JavaFieldLinker(gl.DefaultLinker):
    name = 'javafield'

    def __init__(self, project, prelease, codebase, source, srelease=None,
            filtered_ids=None):
        super(JavaFieldLinker, self).__init__(project, prelease, codebase,
                source, srelease, filtered_ids)
        self.field_kind = CodeElementKind.objects.get(kind='field')
        self.ann_field_kind =\
            CodeElementKind.objects.get(kind='annotation field')
        self.enum_value_kind =\
            CodeElementKind.objects.get(kind='enumeration value')
        self.field_filters = [
                filters.ExceptionFilter(),
                filters.FQNCaseFilter(),
                filters.CustomClassMemberFilter(),
                filters.ImmediateContextFilter(),
                filters.ImmediateContextHierarchyFilter(),
                filters.ContextFilter(ctx.SNIPPET),
                filters.ContextFilter(ctx.SNIPPET, True),
                filters.ContextFilter(ctx.SNIPPET, False, True),
                filters.ContextFilter(ctx.SNIPPET, True, True),
                filters.ContextFilter(ctx.LOCAL),
                filters.ContextFilter(ctx.LOCAL, True),
                filters.ContextFilter(ctx.LOCAL, False, True),
                filters.ContextFilter(ctx.LOCAL, True, True),
                filters.ContextFilter(ctx.MIDDLE),
                filters.ContextFilter(ctx.MIDDLE, True),
                filters.ContextFilter(ctx.GLOBAL),
                filters.ContextFilter(ctx.GLOBAL, True),
                filters.ContextNameSimilarityFilter(),
                filters.AbstractTypeFilter(),
                filters.StrictFilter(),
                ]

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):

        # Annotation Field
        ann_refs = self._get_query(self.ann_field_kind, local_object_id)
        acount = ann_refs.count()
        progress_monitor.info('Annotation Field count: {0}'.format(acount))
        try:
            self._link_ann_fields(queryset_iterator(ann_refs), acount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing annotation fields')
        call_gc()

        # Enumeration Values
        enum_refs = self._get_query(self.enum_value_kind, local_object_id)
        ecount = enum_refs.count()
        progress_monitor.info('Enumeration Value count: {0}'.format(ecount))
        try:
            self._link_enum_values(queryset_iterator(enum_refs), ecount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing enumeration values')
        call_gc()

        # Fields
        field_refs = self._get_query(self.field_kind, local_object_id)
        fcount = field_refs.count()
        progress_monitor.info('Field count: {0}'.format(fcount))
        try:
            self._link_fields(queryset_iterator(field_refs), fcount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing fields')
        call_gc()

    def _link_ann_fields(self, ann_refs, acount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing annotation fields', acount)
        log = gl.LinkerLog(self, self.ann_field_kind.kind)

        for scode_reference in ann_refs:
            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue
            (field_name, fqn_container) = self._get_field_name(scode_reference)
            code_elements = self._get_field_elements(field_name,
                    PREFIX_ANN_FIELD_LINKER, self.ann_field_kind)

            (code_element, potentials) = self.get_code_element(
                    scode_reference, code_elements, field_name, fqn_container,
                    log)
            count += gl.save_link(scode_reference, code_element, potentials,
                    self)

            if not log.custom_filtered:
                reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed ann field', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} ann fields'.format(count))

    def _link_enum_values(self, enum_refs, ecount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing enumeration values', ecount)
        log = gl.LinkerLog(self, self.enum_value_kind.kind)

        for scode_reference in enum_refs:
            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue
            (field_name, fqn_container) = self._get_field_name(scode_reference)
            code_elements = self._get_field_elements(field_name,
                    PREFIX_ENUM_VAL_LINKER, self.enum_value_kind)

            (code_element, potentials) = self.get_code_element(
                    scode_reference, code_elements, field_name, fqn_container,
                    log)
            count += gl.save_link(scode_reference, code_element, potentials,
                    self)

            if not log.custom_filtered:
                reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed enum value', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} enum values'.format(count))

    def _link_fields(self, field_refs, acount, progress_monitor):
        count = 0
        progress_monitor.start('Parsing fields', acount)
        log = gl.LinkerLog(self, self.field_kind.kind)

        for scode_reference in field_refs:
            if self._reject_reference(scode_reference):
                progress_monitor.work('Skipped reference', 1)
                continue
            (field_name, fqn_container) = self._get_field_name(scode_reference)
            code_elements = []
            code_elements.extend(self._get_field_elements(field_name,
                    PREFIX_FIELD_LINKER, self.field_kind))
            code_elements.extend(self._get_field_elements(field_name,
                    PREFIX_ENUM_VAL_LINKER, self.enum_value_kind))
            code_elements.extend(self._get_field_elements(field_name,
                    PREFIX_ANN_FIELD_LINKER, self.ann_field_kind))

            (code_element, potentials) = self.get_code_element(
                    scode_reference, code_elements, field_name, fqn_container,
                    log)
            count += gl.save_link(scode_reference, code_element, potentials,
                    self)

            if not log.custom_filtered:
                reclassify_java(code_element, scode_reference)

            progress_monitor.work('Processed field', 1)

        log.close()
        progress_monitor.done()
        print('Associated {0} fields'.format(count))

    def _get_field_name(self, scode_reference):
        field_name = fqn_container = None

        if scode_reference.snippet != None:
            parts = scode_reference.content.split(HANDLE_SEPARATOR)
            (field_name, fqn_container) = \
                    self._get_field_name_from_snippet(parts)
        else:
            content = je.get_clean_name(scode_reference.content)
            (field_name, fqn) = je.clean_java_name(content)
            if fqn != field_name:
                fqn = je.get_package_name(fqn)
                fqn_container = je.clean_potential_annotation(fqn)

        return (su.safe_strip(field_name), su.safe_strip(fqn_container))

    def _get_field_name_from_snippet(self, parts):
        field_name = fqn_container = None

        try:
            if parts[0].startswith('M'):
                # This is an annotation field
                field_name = parts[2]
            else:
                field_name = parts[3]
            fqn_container = parts[1]
        except Exception:
            logger.exception('Error while parsing field name from snippet')

        return (field_name, fqn_container)

    def _get_field_elements(self, field_name, prefix, kind):
        prefix = '{0}{1}'.format(prefix, cu.get_codebase_key(self.codebase))
        code_elements = cu.get_value(
                prefix,
                field_name,
                gl.get_type_code_elements,
                [field_name, self.codebase, kind, True,
                    FieldElement])

        return code_elements

    def get_code_element(self, scode_reference, code_elements, field_name,
            fqn_container, log):
        log.reset_variables()
        return_code_element = None
        if code_elements is None:
            code_elements = []
        potentials = list(code_elements)
        size = len(code_elements)

        #print('DEBUG FOR {0}:{1}'.format(scode_reference.pk,
            #scode_reference.content))
        #for code_element in code_elements:
            #print(code_element.fqn)

        filter_results = []

        for afilter in self.field_filters:
            finput = filters.FilterInput(scode_reference, potentials,
                    field_name, log, fqn_container, None, filter_results)
            result = afilter.filter(finput)
            potentials = result.potentials
            filter_results.append(result)

        log.custom_filtered = filters.custom_filtered(filter_results)

        potentials_size = len(potentials)
        if potentials_size == 1:
            return_code_element = potentials[0]
        elif potentials_size > 1:
            return_code_element = potentials[0]
            log.arbitrary = True

        # Logging
        log.log_field(field_name, fqn_container, scode_reference,
                return_code_element, potentials, size, filter_results,
                code_elements)
        return (return_code_element, potentials)


class JavaGenericLinker(gl.DefaultLinker):
    name = 'javageneric'

    def __init__(self, project, prelease, codebase, source, srelease=None,
            filtered_ids=None):
        super(JavaGenericLinker, self).__init__(project, prelease, codebase,
                source, srelease, filtered_ids)
        self.unknown_kind = CodeElementKind.objects.get(kind='unknown')
        self.ann_kind = CodeElementKind.objects.get(kind='annotation')
        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.enum_kind = CodeElementKind.objects.get(kind='enumeration')
        self.method_kind = CodeElementKind.objects.get(kind='method')
        self.field_kind = CodeElementKind.objects.get(kind='field')
        self.ann_field_kind =\
            CodeElementKind.objects.get(kind='annotation field')
        self.enum_value_kind =\
            CodeElementKind.objects.get(kind='enumeration value')

        self.class_kinds = set([self.class_kind, self.enum_kind,
            self.ann_kind])
        self.field_kinds = set([self.field_kind, self.ann_field_kind,
            self.enum_value_kind])

        self.class_linker = JavaClassLinker(project, prelease, codebase,
                source, srelease)
        self.method_linker = JavaMethodLinker(project, prelease, codebase,
                source, srelease)
        self.field_linker = JavaFieldLinker(project, prelease, codebase,
                source, srelease)

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):
        unknown_refs = self._get_query(self.unknown_kind, local_object_id)
        ucount = unknown_refs.count()
        progress_monitor.info('Unknown reference count: {0}'.format(ucount))
        try:
            self._link_all_references(queryset_iterator(unknown_refs), ucount,
                    progress_monitor)
        except Exception:
            logger.exception('Error while processing unknown references.')
        call_gc()

    def _link_all_references(self, unknown_refs, ucount, progress_monitor):
        skipped = 0
        class_tuples = []

        progress_monitor.start('Parsing all unknown refs', ucount)
        for reference in unknown_refs:

            if self._reject_reference(reference):
                progress_monitor.work('Rejected reference.', 1)
                continue

            content = su.safe_strip(reference.content)
            if content is None or content == '':
                progress_monitor.work('Empty {0}'.format(reference.pk), 1)
                skipped += 1
                continue

            (simple, fqn) = je.clean_java_name(je.get_clean_name(content))
            prefix = '{0}{1}'.format(PREFIX_GENERIC_LINKER,
                cu.get_codebase_key(self.codebase))
            if reference.source == 'd' or reference.snippet is not None:
                exact = True
                prefix += EXACT
            else:
                exact = False
                prefix += IEXACT
            code_elements = cu.get_value(
                    prefix,
                    simple,
                    gl.get_any_code_element,
                    [simple, self.codebase, exact])

            classified_elements = self._classify_code_elements(code_elements)
            class_tuples.append((reference, simple, fqn) + classified_elements)
            progress_monitor.work('Classified reference', 1)
        progress_monitor.done()

        progress_monitor.info('Classified all refs. Processing now')
        count = self._process_tuples(class_tuples, progress_monitor)

        progress_monitor.info('Associated {0} elements, Skipped {1} elements'
                .format(count, skipped))
        progress_monitor.done()

    def _classify_code_elements(self, code_elements):
        class_code_elements = []
        method_code_elements = []
        field_code_elements = []
        for element in code_elements:
            kind = element.kind
            if kind in self.class_kinds:
                class_code_elements.append(element)
            elif kind == self.method_kind:
                method_code_elements.append(element)
            elif kind in self.field_kinds:
                field_code_elements.append(element)

        # Debug
        #print(len(class_code_elements), len(method_code_elements),
                #len(field_code_elements))

        return (class_code_elements, method_code_elements, field_code_elements)

    def _process_tuples(self, class_tuples, progress_monitor):
        method_tuples = []
        field_tuples = []
        count = 0

        progress_monitor.info('Processing {0} classes'
                .format(len(class_tuples)))
        progress_monitor.start('Processing classes', len(class_tuples))
        log = gl.LinkerLog(self, 'generic-' + self.class_kind.kind)
        for (reference, simple, fqn, class_elements, method_elements,
                field_elements) in class_tuples:
            if len(class_elements) > 0:
                (code_element, potentials) = \
                        self.class_linker.get_code_element(reference,
                                class_elements, simple, fqn, log, True)
                if code_element is not None:
                    count += gl.save_link(reference, code_element,
                            potentials, self)
                else:
                    method_tuples.append((reference, simple, fqn,
                        method_elements, field_elements))
            else:
                method_tuples.append((reference, simple, fqn,
                    method_elements, field_elements))
            progress_monitor.work('Processed a class', 1)

        progress_monitor.done()
        log.close()
        progress_monitor.info('Processed classes')

        progress_monitor.info('Processing {0} methods'
                .format(len(method_tuples)))
        progress_monitor.start('Processing methods', len(method_tuples))
        log = gl.LinkerLog(self, 'generic-' + self.method_kind.kind)
        for (reference, simple, fqn, method_elements,
                field_elements) in method_tuples:
            if len(method_elements) > 0:
                fqn_container = je.get_package_name(fqn)
                if fqn_container == simple:
                    fqn_container = None
                method_info = MethodInfo(simple, fqn_container, None, None)
                (code_element, potentials) =\
                        self.method_linker.get_code_element(reference,
                                method_elements, method_info, log)
                if code_element is not None:
                    count += gl.save_link(reference, code_element,
                            potentials, self)
                else:
                    field_tuples.append((reference, simple, fqn,
                        field_elements))
            else:
                field_tuples.append((reference, simple, fqn, field_elements))
            progress_monitor.work('Processed method', 1)

        progress_monitor.done()
        log.close()
        progress_monitor.info('Processed methods')

        progress_monitor.info('Processing {0} fields'
                .format(len(field_tuples)))
        progress_monitor.start('Processing fields', len(field_tuples))
        log = gl.LinkerLog(self, 'generic-' + self.field_kind.kind)
        for (reference, simple, fqn, field_elements) in field_tuples:
            if len(field_elements) > 0:
                fqn_container = je.get_package_name(fqn)
                if fqn_container == simple:
                    fqn_container = None
                (code_element, potentials) =\
                        self.field_linker.get_code_element(reference,
                                field_elements, simple, fqn_container, log)
                if code_element is not None:
                    count += gl.save_link(reference, code_element,
                            potentials, self)
            progress_monitor.work('Processing fields', 1)
        progress_monitor.done()
        log.close()
        progress_monitor.info('Processed fields')

        return count

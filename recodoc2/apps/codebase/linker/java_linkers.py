from __future__ import unicode_literals
import logging
from django.conf import settings
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import call_gc, queryset_iterator
import docutil.str_util as su
import docutil.cache_util as cu
import codeutil.java_element as je
import codebase.linker.generic_linker as gl
import codebase.linker.filters as filters
from codebase.models import CodeElementKind, SingleCodeReference, \
        CodeElement, ReleaseLinkSet

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
        'enumeration value', 'annotation','enumeration'])
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


def get_package_freq():
    pass


class JavaClassLinker(gl.DefaultLinker):
    name = 'javaclass'

    def __init__(self, project, prelease, codebase, source, srelease=None):
        super(JavaClassLinker, self).__init__(project, prelease, codebase,
                source, srelease)
        self.ann_kind = CodeElementKind.objects.get(kind='annotation')
        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.enum_kind = CodeElementKind.objects.get(kind='enumeration')

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
            if scode_reference.declaration:
                progress_monitor.work('Skipped declaration', 1)
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
            if scode_reference.declaration:
                progress_monitor.work('Skipped declaration', 1)
                continue

            (simple, fqn) = je.get_annotation_name(scode_reference.content,
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
            if scode_reference.declaration:
                progress_monitor.work('Skipped declaration', 1)
                continue

            (simple, fqn) = je.get_annotation_name(scode_reference.content,
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
        print('DEBUG for {0}'.format(scode_reference.content))
        for code_element in code_elements:
            print(code_element.fqn)

        if size > 0:
            if size == 1:
                # There is only one code element.
                return_code_element = code_elements[0]
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
                    potentials = potentials[:1]
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
                    potentials = potentials[:1]
                log.sensitive = True
       
        # Custom filtering
        custom_filter = filters.CustomClassFilter()
        log.custom_filtered = custom_filter.filter(scode_reference,
                return_code_element, log).activated
        if log.custom_filtered:
            return_code_element = potentials = None

        # Logging
        log.log_type(simple, fqn, scode_reference, return_code_element,
                potentials, size)

        return (return_code_element, potentials)
        

class JavaPostClassLinker(gl.DefaultLinker):
    name = 'javapostclass'

    def link_references(self, progress_monitor=NullProgressMonitor(),
            local_object_id=None):
        
        # Get link to filter.
        linksets = ReleaseLinkSet.objects\
                .filter(project_release=self.prelease)\
                .filter(first_link__code_element__kind__is_type=True)

        count = linksets.count()
        progress_monitor.start('Post-Processing Classes', count)
        log = gl.LinkerLog(self, 'type')

        print('LinkSet COUNT {0}'.format(linksets.count()))
        for linkset in queryset_iterator(linksets):
            scode_reference = linkset.code_reference
            lcount = linkset.links.count()
            if lcount <= 1:
                log.log_type('', '', scode_reference,
                        linkset.first_link.code_element,
                        [linkset.first_link], lcount, 'onlyone')
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
                code_element = self._find_package_by_depth(linkset,
                        package_freq)
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
                        [linkset.first_link], lcount, rationale)
            else:
                potentials =\
                    [link.code_element for link in linkset.links.all()]
                log.log_type('', '', scode_reference,
                        linkset.first_link.code_element,
                        potentials, lcount, 'nomatch')

            progress_monitor.work('Processed a linkset.', 1)

        progress_monitor.done()

    def _find_package_by_depth(self, linkset, package_freq):
        pass

    def _find_package_by_freq(self, linkset, package_freq):
        pass


class JavaMethodLinker(gl.DefaultLinker):
    name = 'javamethod'


class JavaFieldLinker(gl.DefaultLinker):
    name = 'javafield'


class JavaGenericLinker(gl.DefaultLinker):
    name = 'javageneric'


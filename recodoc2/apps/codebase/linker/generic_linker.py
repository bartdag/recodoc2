from __future__ import unicode_literals
import os
import codecs
from collections import defaultdict
from django.conf import settings
from codebase.models import SingleCodeReference, CodeElement, ReleaseLinkSet,\
        CodeElementLink, CodeElementKind

DEBUG_LOG = defaultdict(list)


def get_unknown_kind():
    return CodeElementKind.objects.get(kind='unknown')


def get_any_code_element(simple_name, codebase, exact=True):
    if exact:
        return list(CodeElement.objects.\
                filter(simple_name=simple_name).\
                filter(codebase=codebase).all())
    else:
        return list(CodeElement.objects.\
                filter(simple_name__iexact=simple_name).\
                filter(codebase=codebase).all())


def get_type_code_elements(simple_name, codebase, kind, exact=True,
        cls=CodeElement):
    if exact:
        return list(cls.objects.filter(kind=kind).\
                filter(simple_name=simple_name).\
                filter(codebase=codebase).all())
    else:
        return list(cls.objects.filter(kind=kind).\
                filter(simple_name__iexact=simple_name).\
                filter(codebase=codebase).all())


def save_link(scode_reference, code_element, potentials, linker):
    count = 0
    linkset = None
    if code_element is not None:
        linkset = ReleaseLinkSet(
                code_reference=scode_reference,
                project_release=code_element.codebase.project_release
                )
        linkset.save()

        # DEBUG
        #print('Saving first link: {0}'.format(code_element.fqn))

        link = CodeElementLink(
                code_reference=scode_reference,
                code_element=code_element,
                linker_name=linker.name,
                release_link_set=linkset,
                first_link=linkset,
                index=0)
        link.save()
        pk = code_element.pk
        count = 1
    if potentials is not None and len(potentials) > 0:
        index = 1
        for potential in potentials:
            if potential.pk != pk:
                link = CodeElementLink(
                        code_reference=scode_reference,
                        code_element=potential,
                        linker_name=linker.name,
                        release_link_set=linkset,
                        index=index)
                link.save()
                index += 1
    return count


class LinkerLog(object):

    def __init__(self, linker, kind_str):
        self.linker = linker

        log_dir = os.path.join(settings.PROJECT_FS_ROOT,
                linker.project.dir_name)
        if linker.prelease is not None:
            self.release = linker.prelease.release

        self.name = 'linking-{0}-{1}-{2}-{3}-{4}.log'.format(kind_str,
                linker.project.dir_name, self.release, linker.name,
                linker.source)
        file_path = os.path.join(log_dir, self.name)
        self.log_file = codecs.open(file_path, 'a', encoding='utf8')

    def reset_variables(self):
        self.custom_filtered = False
        self.insensitive = False
        self.sensitive = False
        self.one = False
        self.arbitrary = False

    def close(self):
        self.log_file.close()

    def log_type(self, simple_name, fqn, scode_reference, code_element,
            potentials, original_size, rationale=None):
        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        log_file = self.log_file
        log_file.write('Type {0} - {1}\n'.format(simple_name, fqn))
        log_file.write('  Content: {0}\n'.format(scode_reference.content))
        log_file.write('  Original Size: {0}\n'.format(original_size))
        log_file.write('  Final Size: {0}\n'.format(potential_size))
        log_file.write('  URL: {0}\n'.
                format(scode_reference.local_context.url))
        log_file.write('  Ref pk: {0}\n'.format(scode_reference.pk))
        log_file.write('  Local pk: {0}\n'.
                format(scode_reference.local_object_id))

        log_file.write('  Release: {0}\n'.format(self.release))
        log_file.write('  Snippet: {0}\n'.
                format(scode_reference.snippet is not None))
        log_file.write('  Custom Filtered: {0}\n'.format(self.custom_filtered))

        if rationale is not None:
            log_file.write('  Rationale: {0}\n'.format(rationale))

        log_file.write('  Filtering\n')
        log_file.write('    Strategy {0} {1} {2} {3}\n'.format(
            self.one, self.arbitrary, self.insensitive, self.sensitive))

        if code_element is not None:
            log_file.write('  Element: {0}\n'.
                    format(code_element.human_string()))

        if potentials is not None:
            for potential in potentials[1:]:
                log_file.write('  Potential: {0}\n'.
                        format(potential.human_string()))

        log_file.write('\n\n')
        self.debug_log_type(simple_name, fqn, scode_reference, code_element,
                potentials, original_size, rationale)

    def debug_log_type(self, simple_name, fqn, scode_reference, code_element,
            potentials, original_size, rationale=None):
        if not settings.DEBUG:
            return

        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        type_log = {}
        type_log['original size'] = original_size
        type_log['final size'] = potential_size
        type_log['rationale'] = rationale
        type_log['custom filtered'] = self.custom_filtered
        type_log['linker'] = self.linker.name

        DEBUG_LOG[scode_reference.pk].append(type_log)

    def log_method(self, method_info, scode_reference, return_code_element,
            potentials, original_size, fresults):

        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        log_file = self.log_file
        log_file.write('Method {0} - {1}\n'.format(method_info.method_name,
            method_info.type_params))
        log_file.write('  Content: {0}\n'.format(scode_reference.content))
        log_file.write('  Original Size: {0}\n'.format(original_size))
        log_file.write('  Final Size: {0}\n'.format(potential_size))
        log_file.write('  URL: {0}\n'.
                format(scode_reference.local_context.url))
        log_file.write('  Ref pk: {0}\n'.format(scode_reference.pk))
        log_file.write('  Local pk: {0}\n'.
                format(scode_reference.local_object_id))

        log_file.write('  Release: {0}\n'.format(self.release))
        log_file.write('  Snippet: {0}\n'.
                format(scode_reference.snippet is not None))
        log_file.write('  Custom Filtered: {0}\n'.format(self.custom_filtered))

        log_file.write('  Filtering\n')
        for fresult in fresults:
            log_file.write('    {0} {1}: {2} - {3}\n'.format(
                fresult.name, fresult.options, fresult.activated,
                len(fresult.potentials)))

        if return_code_element is not None:
            log_file.write('  Element: {0}\n'.
                    format(return_code_element.human_string()))

        if potentials is not None:
            for potential in potentials[1:]:
                log_file.write('  Potential: {0}\n'.
                        format(potential.human_string()))

        log_file.write('\n\n')

        self.debug_log_method(method_info, scode_reference,
                return_code_element, potentials, original_size, fresults)

    def debug_log_method(self, method_info, scode_reference,
            return_code_element, potentials, original_size, fresults):
        if not settings.DEBUG:
            return

        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        method_log = {}
        method_log['original size'] = original_size
        method_log['final size'] = potential_size
        method_log['custom filtered'] = self.custom_filtered
        method_log['linker'] = self.linker.name
        for fresult in fresults:
            method_log[fresult.name] = (fresult.activated,
                    len(fresult.potentials))

        DEBUG_LOG[scode_reference.pk].append(method_log)

    def log_field(self, field_name, fqn_container, scode_reference,
            return_code_element, potentials, original_size, fresults):

        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        log_file = self.log_file
        log_file.write('Field {0}.{1}\n'.format(fqn_container,
            field_name))
        log_file.write('  Content: {0}\n'.format(scode_reference.content))
        log_file.write('  Original Size: {0}\n'.format(original_size))
        log_file.write('  Final Size: {0}\n'.format(potential_size))
        log_file.write('  URL: {0}\n'.
                format(scode_reference.local_context.url))
        log_file.write('  Ref pk: {0}\n'.format(scode_reference.pk))
        log_file.write('  Local pk: {0}\n'.
                format(scode_reference.local_object_id))

        log_file.write('  Release: {0}\n'.format(self.release))
        log_file.write('  Snippet: {0}\n'.
                format(scode_reference.snippet is not None))
        log_file.write('  Custom Filtered: {0}\n'.format(self.custom_filtered))

        log_file.write('  Filtering\n')
        for fresult in fresults:
            log_file.write('    {0} {1}: {2} - {3}\n'.format(
                fresult.name, fresult.options, fresult.activated,
                len(fresult.potentials)))

        if return_code_element is not None:
            log_file.write('  Element: {0}\n'.
                    format(return_code_element.human_string()))

        if potentials is not None:
            for potential in potentials[1:]:
                log_file.write('  Potential: {0}\n'.
                        format(potential.human_string()))

        log_file.write('\n\n')

        self.debug_log_field(field_name, fqn_container, scode_reference,
                return_code_element, potentials, original_size, fresults)

    def debug_log_field(self, field_name, fqn_container, scode_reference,
            return_code_element, potentials, original_size, fresults):
        if not settings.DEBUG:
            return

        potential_size = 0
        if potentials is not None:
            potential_size = len(potentials)

        field_log = {}
        field_log['original size'] = original_size
        field_log['final size'] = potential_size
        field_log['custom filtered'] = self.custom_filtered
        field_log['linker'] = self.linker.name
        for fresult in fresults:
            field_log[fresult.name] = (fresult.activated,
                    len(fresult.potentials))

        DEBUG_LOG[scode_reference.pk].append(field_log)


class DefaultLinker(object):

    def __init__(self, project, prelease, codebase, source, srelease=None):
        self.project = project
        self.prelease = prelease
        self.codebase = codebase
        self.source = source
        self.srelease = srelease

    def _get_query(self, kind_hint, local_object_id):
        refs = SingleCodeReference.objects.\
                filter(kind_hint=kind_hint).\
                filter(source=self.source).\
                filter(project=self.project)
        if self.srelease is not None:
            refs = refs.filter(project_release=self.srelease)

        # For debug:
        if local_object_id is not None:
            refs = refs.filter(local_object_id=local_object_id)

        return refs

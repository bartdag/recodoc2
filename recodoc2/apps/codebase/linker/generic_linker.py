from __future__ import unicode_literals
import os
import codecs
from django.conf import settings
from codebase.models import SingleCodeReference, CodeElement, ReleaseLinkSet,\
        CodeElementLink, CodeElementKind


def get_unknown_kind():
    return CodeElementKind.objects.get(kind='unknown')


def get_type_code_elements(simple_name, codebase, kind):
    return list(CodeElement.objects.filter(kind=kind).\
            filter(simple_name=simple_name).\
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
        for potential in enumerate(potentials):
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
        if linker.srelease is not None:
            self.release = linker.srelease.release
        else:
            self.release = 'default'
        
        self.name = 'linking-{0}-{1}-{2}-{3}-{4}.log'.format(kind_str, 
                linker.project.dir_name, release, linker.name, linker.source)
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
            potentials, original_size):
        log_file = self.log_file
        log_file.write('Type {0} - {1}\n'.format(simple_name, fqn))
        log_file.write('  Original Size: {0}\n'.format(original_size))
        log_file.write('  Final Size: {0}\n'.format(len(potentials)))
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

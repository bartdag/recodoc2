from __future__ import unicode_literals
import os
import re
from django.conf import settings
from django.db import transaction

from docutil.progress_monitor import CLIProgressMonitor
from docutil.commands_util import mkdir_safe, dump_model, load_model,\
    import_clazz
from project.models import ProjectRelease
from project.actions import DOC_PATH
from codebase.models import CodeBase, CodeBaseDiff
from recommender.models import CodePattern, CodePatternCoverage
from recommender.parser.pattern_coverage import compute_coverage
from doc.models import DocumentStatus, Document, Page, Section, DocDiff
from doc.parser.generic_parser import parse
from doc.parser.doc_diff import DocDiffer, DocLinkerDiffer


def get_doc_path(pname, dname=None, release=None, root=False):
    if root:
        doc_key = ''
    else:
        doc_key = dname + release
    basepath = settings.PROJECT_FS_ROOT
    doc_path = os.path.join(basepath, pname, DOC_PATH, doc_key)
    return doc_path


def create_doc_local(pname, dname, release, syncer, input_url=None):
    doc_key = dname + release
    doc_path = get_doc_path(pname, dname, release)
    mkdir_safe(doc_path)

    model = DocumentStatus(syncer=syncer, input_url=input_url)
    dump_model(model, pname, DOC_PATH, doc_key)


def create_doc_db(pname, dname, release, url, syncer, parser):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    document = Document(title=dname, project_release=prelease, url=url,
            parser=parser, syncer=syncer)
    document.save()
    return document


def list_doc_db(pname):
    docs = []
    for doc in Document.objects.filter(
            project_release__project__dir_name=pname):
        docs.append('{0}: {1} ({2})'.format(doc.pk, doc.title, doc.url))
    return docs


def list_doc_local(pname):
    doc_path = get_doc_path(pname, root=True)
    local_docs = []
    for member in os.listdir(doc_path):
        if os.path.isdir(os.path.join(doc_path, member)):
            local_docs.append(member)
    return local_docs


def sync_doc(pname, dname, release):
    doc_key = dname + release
    doc_path = get_doc_path(pname, dname, release)
    model = load_model(pname, DOC_PATH, doc_key)
    syncer = import_clazz(model.syncer)(model.input_url, doc_path)
    pages = syncer.sync()
    model.pages = pages
    dump_model(model, pname, DOC_PATH, doc_key)


def clear_doc_elements(pname, dname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    document = Document.objects.filter(project_release=prelease).\
            filter(title=dname)[0]
    query = Section.objects.filter(page__document=document)
    print('Deleting %i sections' % query.count())
    for section in query.all():
        section.code_references.all().delete()
        section.code_snippets.all().delete()
        section.delete()
    Page.objects.filter(document=document).delete()


@transaction.autocommit
def parse_doc(pname, dname, release, parse_refs=True):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    document = Document.objects.filter(project_release=prelease).\
            filter(title=dname)[0]
    doc_key = dname + release
    model = load_model(pname, DOC_PATH, doc_key)
    progress_monitor = CLIProgressMonitor()
    parse(document, model.pages, parse_refs, progress_monitor)

    return document


@transaction.autocommit
def diff_doc(pname, dname, release1, release2):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    document_from = Document.objects.filter(project_release=prelease1).\
            filter(title=dname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    document_to = Document.objects.filter(project_release=prelease2).\
            filter(title=dname)[0]

    differ = DocDiffer()
    return differ.diff_docs(document_from, document_to)


@transaction.autocommit
def diff_links(pname, dname, release1, release2):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    document_from = Document.objects.filter(project_release=prelease1).\
            filter(title=dname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    document_to = Document.objects.filter(project_release=prelease2).\
            filter(title=dname)[0]
    doc_diff = DocDiff.objects.filter(document_from=document_from).\
            get(document_to=document_to)
    doc_linker_differ = DocLinkerDiffer(doc_diff)
    (added_links, removed_links) = doc_linker_differ.diff_links()
    print('Added links: {0}'.format(len(added_links)))
    print('Removed links: {0}'.format(len(removed_links)))


def compute_family_coverage(pname, bname, release, dname, srelease):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    psrelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=srelease)[0]
    document = Document.objects.filter(project_release=psrelease).\
            filter(title=dname)[0]
    patterns = CodePattern.objects.filter(codebase=codebase).all()
    progress_monitor = CLIProgressMonitor(min_step=1.0)

    compute_coverage(patterns, 'd', document, progress_monitor)


def clear_pattern_coverage(pname, bname, release, dname, srelease):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    psrelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=srelease)[0]
    document = Document.objects.filter(project_release=psrelease).\
            filter(title=dname)[0]

    query = CodePatternCoverage.objects.\
            filter(resource_object_id=document.pk).\
            filter(pattern__codebase=codebase)

    print('Deleting {0} pattern coverages'.format(query.count()))

    query.delete()


def remove_page(pname, dname, release, url_regex):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    document = Document.objects.filter(project_release=prelease).\
            filter(title=dname)[0]
    pattern = re.compile(url_regex)
    to_delete = []
    for page in document.pages.all():
        if pattern.search(page.url):
            to_delete.append(page)
    for page in to_delete:
        print('Page {0} deleted'.format(page.url))
        page.delete()

    print('{0} pages deleted'.format(len(to_delete)))


def show_new_new_links(pname, bname, dname, release1, release2):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    document_from = Document.objects.filter(project_release=prelease1).\
            filter(title=dname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    document_to = Document.objects.filter(project_release=prelease2).\
            filter(title=dname)[0]
    doc_diff = DocDiff.objects.filter(document_from=document_from).\
            get(document_to=document_to)

    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]
    code_diff = CodeBaseDiff.objects.filter(codebase_from=codebase1).\
            filter(codebase_to=codebase2)[0]

    # We only care about these kinds for now.
    types = set(code_diff.added_types.all())
    methods = set(code_diff.added_methods.all())
    fields = set(code_diff.added_fields.all())
    all_elements = types.union(methods).union(fields)
    links = doc_diff.link_changes.filter(link_from__isnull=True).all()
    print('Total links: {0}'.format(links.count()))
    for link in links:
        code_element = link.link_to.code_element
        container = code_element.containers.all()[0]
        section_title = link.link_to.code_reference.local_context.title
        page_title = link.link_to.code_reference.global_context.title
        if code_element in all_elements:
            print('Link to {0} was added in {1} ({2})'.format(code_element,
                section_title, page_title))
        elif container in types:
            print('Link to {0} was added in {1} ({2}'.format(code_element,
                section_title, page_title))
        #else:
            #print('OLD: Link to {0} was added in {1} ({2}'.format(code_element,
                #section_title, page_title))


# Functions

def show_section(section_pk):
    section = Section.objects.get(pk=section_pk)
    print(section.title)
    print(section.url)
    print(section.word_count)
    print(section.pk)
    count = 0
    for code_reference in section.code_references.all():
        link = code_reference.first_link()
        if link is not None:
            count += 1
            link_str = link.code_element.human_string()
        else:
            link_str = ''
        print('{0};;{1}'.format(code_reference.content, link_str))
    print('Total links: {0}'.format(count))


def show_sectionn(number, release=None):
    section = Section.objects.filter(number=number)
    if release is None:
        pk = section.all()[0].pk
    else:
        pk = \
            section.filter(page__document__project_release__release=release).\
                all()[0].pk
    show_section(pk)

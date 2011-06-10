from __future__ import unicode_literals
import os
from django.conf import settings
from django.db import transaction

from docutil.progress_monitor import CLIProgressMonitor
from docutil.commands_util import mkdir_safe, dump_model, load_model,\
    import_clazz
from project.models import ProjectRelease
from project.actions import DOC_PATH
from doc.models import DocumentStatus, Document, Page, Section
from doc.parser.generic_parser import parse
from doc.parser.doc_diff import DocDiffer


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

# Functions

def show_section(section_pk):
    section = Section.objects.get(pk=section_pk)
    print(section.title)
    print(section.url)
    print(section.word_count)
    print(section.pk)
    for code_reference in section.code_references.all():
        link = code_reference.first_link()
        if link is not None:
            link_str = link.code_element.human_string()
        else:
            link_str = ''
        print('{0};{1}'.format(code_reference.content, link_str))

from __future__ import unicode_literals
import os
from django.conf import settings

from docutil.commands_util import mkdir_safe, dump_model, load_model,\
    import_clazz
from project.models import ProjectRelease
from project.actions import DOC_PATH
from doc.models import DocumentStatus, Document


def get_doc_path(pname, dname=None, release=None, root=False):
    if root:
        doc_key = ''
    else:
        doc_key = dname + release
    basepath = settings.PROJECT_FS_ROOT
    doc_path = os.path.join(basepath, pname, DOC_PATH, doc_key)
    return doc_path


def create_doc_local(pname, dname, release, syncer):
    doc_key = dname + release
    doc_path = get_doc_path(pname, dname, release)
    mkdir_safe(doc_path)

    model = DocumentStatus(syncer=syncer)
    dump_model(model, pname, DOC_PATH, doc_key)


def create_doc_db(pname, dname, release, url, parser, syncer):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    document = Document(title=dname, project_release=prelease, url=url,
            parser=parser, syncer=syncer)
    document.save()


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
    doc_key = pname + release
    doc_path = get_doc_path(pname, dname, release)
    model = load_model(pname, DOC_PATH, doc_key)
    syncer = import_clazz(model.syncer)(doc_path)
    pages = syncer.sync()
    model.pages = pages
    dump_model(model, pname, DOC_PATH, doc_key)
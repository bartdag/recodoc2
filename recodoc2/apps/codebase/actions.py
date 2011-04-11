from __future__ import unicode_literals
import subprocess
import time
import os
import logging
import enchant
from py4j.java_gateway import JavaGateway
from django.conf import settings
from django.db import transaction
from docutil.str_util import tokenize
from docutil.cache_util import get_value, get_codebase_key
from docutil.commands_util import mkdir_safe, import_clazz
from docutil.progress_monitor import CLILockProgressMonitor
from project.models import ProjectRelease
from project.actions import CODEBASE_PATH
from codebase.models import CodeBase, CodeElementKind, CodeElement


PROJECT_FILE = '.project'
CLASSPATH_FILE = '.classpath'
BIN_FOLDER = 'bin'
SRC_FOLDER = 'src'
LIB_FOLDER = 'lib'

PARSERS = dict(settings.CODE_PARSERS, **settings.CUSTOM_CODE_PARSERS)

PREFIX_CODEBASE_CODE_WORDS = ''.join([settings.CACHE_MIDDLEWARE_KEY_PREFIX,
                                'cb_codewords'])
PREFIX_PROJECT_CODE_WORDS = ''.join([settings.CACHE_MIDDLEWARE_KEY_PREFIX,
                                'project_codewords'])

logger = logging.getLogger("recodoc.codebase.actions")


def start_eclipse():
    eclipse_call = settings.ECLIPSE_COMMAND
    p = subprocess.Popen([eclipse_call])
    print('Process started: {0}'.format(p.pid))
    time.sleep(7)
    check_eclipse()

    return p.pid


def stop_eclipse():
    gateway = JavaGateway()
    try:
        gateway.entry_point.closeEclipse()
        time.sleep(1)
        gateway.shutdown()
    except Exception:
        pass
    try:
        gateway.close()
    except Exception:
        pass


def check_eclipse():
    '''Check that Eclipse is started and that recodoc can communicate with
       it.'''
    gateway = JavaGateway()
    try:
        success = gateway.entry_point.getServer().getListeningPort() > 0
    except Exception:
        success = False

    if success:
        print('Connection to Eclipse: OK')
    else:
        print('Connection to Eclipse: ERROR')

    gateway.close()

    return success


def get_codebase_path(pname, bname='', release='', root=False):
    project_key = pname + bname + release
    basepath = settings.PROJECT_FS_ROOT
    if not root:
        return os.path.join(basepath, pname, CODEBASE_PATH, project_key)
    else:
        return os.path.join(basepath, pname, CODEBASE_PATH)


def create_code_db(pname, bname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codeBase = CodeBase(name=bname, project_release=prelease)
    codeBase.save()

    return codeBase


def create_code_local(pname, bname, release):
    '''Create an Eclipse Java Project on the filesystem.'''
    project_key = pname + bname + release
    codebase_path = get_codebase_path(pname, bname, release)
    mkdir_safe(codebase_path)

    with open(os.path.join(codebase_path, PROJECT_FILE), 'w') as project_file:
        project_file.write("""<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
    <name>{0}</name>
    <comment></comment>
    <projects>
    </projects>
    <buildSpec>
        <buildCommand>
            <name>org.eclipse.jdt.core.javabuilder</name>
            <arguments>
            </arguments>
        </buildCommand>
    </buildSpec>
    <natures>
        <nature>org.eclipse.jdt.core.javanature</nature>
    </natures>
</projectDescription>
""".format(project_key))

    with open(os.path.join(codebase_path, CLASSPATH_FILE), 'w') as \
        classpath_file:
        classpath_file.write("""<?xml version="1.0" encoding="UTF-8"?>
<classpath>
    <classpathentry kind="src" path="src"/>
    <classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER"/>
    <classpathentry kind="output" path="bin"/>
</classpath>
""")

    mkdir_safe(os.path.join(codebase_path, SRC_FOLDER))
    mkdir_safe(os.path.join(codebase_path, BIN_FOLDER))
    mkdir_safe(os.path.join(codebase_path, LIB_FOLDER))


def link_eclipse(pname, bname, release):
    '''Add the Java Project created with create_code_local to the Eclipse
       workspace.'''
    project_key = pname + bname + release
    codebase_path = get_codebase_path(pname, bname, release)

    gateway = JavaGateway()
    workspace = gateway.jvm.org.eclipse.core.resources.ResourcesPlugin.\
            getWorkspace()
    root = workspace.getRoot()
    path = gateway.jvm.org.eclipse.core.runtime.Path(os.path.join(
        codebase_path, PROJECT_FILE))
    project_desc = workspace.loadProjectDescription(path)
    new_project = root.getProject(project_key)
    nmonitor = gateway.jvm.org.eclipse.core.runtime.NullProgressMonitor()
#    gateway.jvm.py4j.GatewayServer.turnLoggingOn()
    # To avoid workbench problem (don't know why it needs some time).
    time.sleep(1)
    new_project.create(project_desc, nmonitor)
    new_project.open(nmonitor)
    gateway.close()


def list_code_db(pname):
    code_bases = []
    for code_base in CodeBase.objects.\
            filter(project_release__project__dir_name=pname):
        code_bases.append('{0}: {1} ({2})'.format(
            code_base.pk,
            code_base.project_release.project.dir_name,
            code_base.project_release.release))
    return code_bases


def list_code_local(pname):
    basepath = settings.PROJECT_FS_ROOT
    code_path = os.path.join(basepath, pname, CODEBASE_PATH)
    local_code_bases = []
    for member in os.listdir(code_path):
        if os.path.isdir(os.path.join(code_path, member)):
            local_code_bases.append(member)
    return local_code_bases


@transaction.commit_on_success
def create_code_element_kinds():
    kinds = []

    #NonType
    kinds.append(CodeElementKind(kind='package', is_type=False))

    # Type
    kinds.append(CodeElementKind(kind='class', is_type=True))
    kinds.append(CodeElementKind(kind='annotation', is_type=True))
    kinds.append(CodeElementKind(kind='enumeration', is_type=True))
#    kinds.append(CodeElementKind(kind='interface', is_type = True))

    # Members
    kinds.append(CodeElementKind(kind='method'))
    kinds.append(CodeElementKind(kind='method family'))
    kinds.append(CodeElementKind(kind='method parameter', is_attribute=True))
    kinds.append(CodeElementKind(kind='field'))
    kinds.append(CodeElementKind(kind='enumeration value'))
    kinds.append(CodeElementKind(kind='annotation field', is_attribute=True))

    # XML
    kinds.append(CodeElementKind(kind='xml type', is_type=True))
    kinds.append(CodeElementKind(kind='xml element'))
    kinds.append(CodeElementKind(kind='xml attribute', is_attribute=True))
    kinds.append(CodeElementKind(kind='xml attribute value', is_value=True))
    kinds.append(CodeElementKind(kind='xml element type', is_type=True))
    kinds.append(CodeElementKind(kind='xml attribute type', is_type=True))
    kinds.append(CodeElementKind(kind='xml attribute value type',
        is_type=True))
    kinds.append(CodeElementKind(kind='property type', is_type=True))
    kinds.append(CodeElementKind(kind='property name'))
    kinds.append(CodeElementKind(kind='property value', is_value=True))

    #Files
    kinds.append(CodeElementKind(kind='xml file', is_file=True))
    kinds.append(CodeElementKind(kind='ini file', is_file=True))
    kinds.append(CodeElementKind(kind='conf file', is_file=True))
    kinds.append(CodeElementKind(kind='properties file', is_file=True))
    kinds.append(CodeElementKind(kind='log file', is_file=True))
    kinds.append(CodeElementKind(kind='jar file', is_file=True))
    kinds.append(CodeElementKind(kind='java file', is_file=True))
    kinds.append(CodeElementKind(kind='python file', is_file=True))
    kinds.append(CodeElementKind(kind='hbm file', is_file=True))

    # Other
    kinds.append(CodeElementKind(kind='unknown'))

    for kind in kinds:
        kind.save()


@transaction.autocommit
def parse_code(pname, bname, release, parser_name, opt_input=None):
    '''

    autocommit is necessary here to prevent goofs. Parsers can be
    multi-threaded and transaction management in django uses thread local...
    '''
    project_key = pname + bname + release
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]

    parser_cls_name = PARSERS[parser_name]
    parser_cls = import_clazz(parser_cls_name)
    parser = parser_cls(codebase, project_key, opt_input)
    parser.parse(CLILockProgressMonitor())

    return codebase


def clear_code_elements(pname, bname, release, parser_name='-1'):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    query = CodeElement.objects.filter(codebase=codebase)
    if parser_name != '-1':
        query = query.filter(parser=parser_name)
    query.delete()


def compute_code_words(codebase):
    d = enchant.Dict('en-US')
    
    elements = CodeElement.objects.\
            filter(codebase=codebase).\
            filter(kind__is_type=True).\
            iterator()

    code_words = set()
    for element in elements:
        simple_name = element.simple_name
        tokens = tokenize(simple_name)
        if len(tokens) > 1:
            code_words.add(simple_name.lower())
        else:
            simple_name = simple_name.lower()
            if not d.check(simple_name):
                code_words.add(simple_name)
    
    logger.debug('Computed {0} code words for codebase {1}'.format(
        len(code_words), str(codebase)))
                
    return code_words


def compute_project_code_words(codebases):
    code_words = set()
    for codebase in codebases:
        code_words.update(
                get_value(PREFIX_CODEBASE_CODE_WORDS,
                    get_codebase_key(codebase),
                    compute_code_words,
                    [codebase])
                )
    return code_words


def get_project_code_words(project):
    codebases = CodeBase.objects.filter(project_release__project=project).all()
    return get_value(
            PREFIX_PROJECT_CODE_WORDS,
            project.pk,
            compute_project_code_words,
            [codebases]
            )


from __future__ import unicode_literals
import subprocess
import time
import os
import signal
from py4j.java_gateway import JavaGateway
from django.conf import settings
from django.db import transaction
from docutil.commands_util import mkdir_safe
from project.models import Project, ProjectRelease
from project.actions import CODEBASE_PATH
from codebase.models import CodeBase, CodeElementKind


PROJECT_FILE = '.project'
CLASSPATH_FILE = '.classpath'
BIN_FOLDER = 'bin'
SRC_FOLDER = 'src'
LIB_FOLDER = 'lib'


def start_eclipse():
    eclipse_call = settings.ECLIPSE_COMMAND
    p = subprocess.Popen([eclipse_call])
    print('Process started: {0}'.format(p.pid))
    time.sleep(7)
    check_eclipse()

    return p.pid


def stop_eclipse(pid=None):
    gateway = JavaGateway()
    try:
        gateway.entry_point.shutdown()
    except:
        pass
    try:
        gateway.close()
    except:
        pass

    if pid is not None:
        try:
            pgid = os.getpgid(pid)
            # Complicated loop to kill a child process...
            # Cannot kill the group or it will kill itself...
            # Cannot kill the pid because on Linux, it might
            # not kill the child process (the jvm)
            for temppid in os.listdir('/proc'):
                if temppid.isdigit():
                    ipid = int(temppid)
                    # Hack that should work most of the time...
                    if ipid > pid:
                        temppgid = os.getpgid(pid)
                        if temppgid == pgid:
                            os.kill(pid, signal.SIGTERM)
                            os.kill(ipid, signal.SIGTERM)
                            break
        except:
            pass

        # Should work on windows...
        try:
            os.kill(pid, signal.SIGTERM)
        except:
            pass


def check_eclipse():
    '''Check that Eclipse is started and that recodoc can communicate with
       it.'''
    gateway = JavaGateway()
    try:
        success = gateway.entry_point.getServer().getListeningPort() > 0
    except:
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
    '''Add the Java Project created with create_code_local to the Eclipse workspace.'''
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
    for code_base in CodeBase.objects.filter(project_release__project__dir_name=pname):
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
    kinds.append(CodeElementKind(kind='enumeration value', is_attribute=True))
    kinds.append(CodeElementKind(kind='annotation field', is_attribute=True))
    
    # XML
    kinds.append(CodeElementKind(kind='xml type', is_type=True))
    kinds.append(CodeElementKind(kind='xml element'))
    kinds.append(CodeElementKind(kind='xml attribute', is_attribute=True))
    kinds.append(CodeElementKind(kind='xml attribute value', is_value=True))
    kinds.append(CodeElementKind(kind='xml element type', is_type=True))
    kinds.append(CodeElementKind(kind='xml attribute type', is_type=True))
    kinds.append(CodeElementKind(kind='xml attribute value type', is_type=True))
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

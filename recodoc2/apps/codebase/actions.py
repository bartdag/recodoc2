from __future__ import unicode_literals
from math import sqrt
import subprocess
import time
import os
import logging
import codecs
from collections import defaultdict
from functools import partial
#from traceback import print_exc
from lxml import etree
import enchant
from py4j.java_gateway import JavaGateway
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from codeutil.parser import is_valid_match, find_parent_reference,\
        create_match
from codeutil.xml_element import XMLStrategy, XML_LANGUAGE, is_xml_snippet,\
        is_xml_lines
from codeutil.java_element import ClassMethodStrategy, MethodStrategy,\
        FieldStrategy, OtherStrategy, AnnotationStrategy, SQLFilter,\
        BuilderFilter, JAVA_LANGUAGE, is_java_snippet, is_java_lines,\
        is_exception_trace_lines, JAVA_EXCEPTION_TRACE, clean_java_name,\
        can_merge_java, MacroFilter
from codeutil.other_element import FileStrategy, IgnoreStrategy,\
        IGNORE_KIND, EMAIL_PATTERN_RE, URL_PATTERN_RE, OTHER_LANGUAGE,\
        is_empty_lines, is_log_lines, LOG_LANGUAGE
from codeutil.reply_element import REPLY_LANGUAGE, is_reply_lines,\
        is_reply_header, STOP_LANGUAGE, is_rest_reply
from docutil.str_util import tokenize, find_sentence, find_paragraph, split_pos
from docutil.cache_util import get_value, get_codebase_key
from docutil.commands_util import mkdir_safe, import_clazz, download_html_tree
from docutil.progress_monitor import CLILockProgressMonitor, CLIProgressMonitor
from docutil import cache_util
from project.models import ProjectRelease, Project
from project.actions import CODEBASE_PATH
from codebase.models import CodeBase, CodeElementKind, CodeElement,\
        SingleCodeReference, CodeSnippet, CodeElementFilter, ReleaseLinkSet
from codebase.parser.java_diff import JavaDiffer


PROJECT_FILE = '.project'
CLASSPATH_FILE = '.classpath'
BIN_FOLDER = 'bin'
SRC_FOLDER = 'src'
LIB_FOLDER = 'lib'

PARSERS = dict(settings.CODE_PARSERS, **settings.CUSTOM_CODE_PARSERS)

SNIPPET_PARSERS = dict(
        settings.CODE_SNIPPET_PARSERS,
        **settings.CUSTOM_CODE_SNIPPET_PARSERS)

LINKERS = dict(settings.LINKERS, **settings.CUSTOM_LINKERS)


PREFIX_CODEBASE_CODE_WORDS = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
                                'cb_codewords'
PREFIX_PROJECT_CODE_WORDS = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
                                'project_codewords'

PREFIX_CODEBASE_FILTERS = settings.CACHE_MIDDLEWARE_KEY_PREFIX +\
                                'cb_filters'

JAVA_KINDS_HIERARCHY = {'field': 'class',
                        'method': 'class',
                        'method parameter': 'method'}

XML_KINDS_HIERARCHY = {'xml attribute': 'xml element',
                       'xml attribute value': 'xml attribute'}

ALL_KINDS_HIERARCHIES = dict(JAVA_KINDS_HIERARCHY, **XML_KINDS_HIERARCHY)

# Constants used by filter
xtext = etree.XPath("string()")

xpackage = etree.XPath("//h2")

xmember_tables = etree.XPath("//body/table")

xmembers = etree.XPath("tr/td[1]")

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
    kinds.append(CodeElementKind(kind='annotation field'))

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


@transaction.autocommit
def parse_snippets(pname, source, parser_name):
    project = Project.objects.get(dir_name=pname)
    parser_cls_name = SNIPPET_PARSERS[parser_name]
    parser_cls = import_clazz(parser_cls_name)
    snippet_parser = parser_cls(project, source)
    snippet_parser.parse(CLILockProgressMonitor())


def clear_snippets(pname, language, source):
    project = Project.objects.get(dir_name=pname)
    to_delete = SingleCodeReference.objects.\
            filter(snippet__language=language).\
            filter(source=source).\
            filter(project=project)
    print('Snippets to delete: %i' % to_delete.count())
    to_delete.delete()


def clear_code_elements(pname, bname, release, parser_name='-1'):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    query = CodeElement.objects.filter(codebase=codebase)
    if parser_name != '-1':
        query = query.filter(parser=parser_name)
    query.delete()


def diff_codebases(pname, bname, release1, release2):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase_from = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase_to = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    # Maybe later, this will be more generic
    differ = JavaDiffer()
    return differ.diff(codebase_from, codebase_to)


def create_filter_file(file_path, url):
    new_file_path = os.path.join(settings.PROJECT_FS_ROOT, file_path)
    if os.path.exists(new_file_path):
        mode = 'a'
    else:
        mode = 'w'

    with open(new_file_path, mode) as afile:
        tree = download_html_tree(url)
        package_name = get_package_name(tree)
        tables = xmember_tables(tree)
        for table in tables[1:-1]:
            for member in xmembers(table):
                member_string = "{0}.{1}".format(package_name, xtext(member))
                afile.write(member_string + '\n')
                print(member_string)


def add_filter(pname, bname, release, filter_files):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    count = countfilter = 0
    for filterfile in filter_files.split(','):
        file_path = os.path.join(settings.PROJECT_FS_ROOT,
                filterfile.strip() + '.txt')
        with open(file_path) as afile:
            for line in afile.readlines():
                code_filter = CodeElementFilter(
                        codebase=codebase,
                        fqn=line.strip())
                code_filter.save()
                countfilter += 1
            count += 1
    print('Added {0} filter groups and {1} individual filters.'
            .format(count, countfilter))


def add_a_filter(pname, bname, release, filter_fqn, include_snippet=True,
        one_ref_only=False, include_member=False):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    code_filter = CodeElementFilter(
            codebase=codebase,
            fqn=filter_fqn,
            include_snippet=include_snippet,
            one_ref_only=one_ref_only,
            include_member=include_member)
    code_filter.save()


def link_code(pname, bname, release, linker_name, source, source_release=None,
        local_object_id=None, filtered_ids_path=None, filtered_ids_level=None):
    project = Project.objects.get(dir_name=pname)
    prelease = ProjectRelease.objects.filter(project=project).\
            filter(release=release)[0]
    if source_release is not None and source_release != '-1':
        srelease = ProjectRelease.objects.filter(project=project).\
            filter(release=source_release)[0]
    else:
        srelease = None
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]

    (f_ids, f_ids_level) = compute_f_ids(filtered_ids_path, filtered_ids_level)
    if f_ids is not None:
        count = len(f_ids)
    else:
        count = 0

    linker_cls_name = LINKERS[linker_name]
    linker_cls = import_clazz(linker_cls_name)
    linker = linker_cls(project, prelease, codebase, source, srelease,
            (f_ids, f_ids_level))

    progress_monitor = CLIProgressMonitor(min_step=1.0)
    progress_monitor.info('Cache Count {0} miss of {1}'
            .format(cache_util.cache_miss, cache_util.cache_total))
    progress_monitor.info('Ref ids to keep: {0}'.format(count))

    start = time.clock()

    linker.link_references(progress_monitor, local_object_id)

    stop = time.clock()
    progress_monitor.info('Cache Count {0} miss of {1}'
            .format(cache_util.cache_miss, cache_util.cache_total))
    progress_monitor.info('Time: {0}'.format(stop - start))


def clear_links(pname, release, source='-1'):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    query = ReleaseLinkSet.objects.filter(project_release=prelease)
    if source != '-1':
        query = query.filter(code_reference__source=source)
    query.delete()


def restore_kinds(pname, release='-1', source='-1'):
    project = Project.objects.get(dir_name=pname)
    query = SingleCodeReference.objects.filter(project=project)
    if release != '-1':
        prelease = ProjectRelease.objects.filter(project=project).\
                filter(release=release)[0]
        query = query.filter(project_release=prelease)
    if source != '-1':
        query = query.filter(source=source)

    count = query.count()

    progress_monitor = CLIProgressMonitor(min_step=1.0)
    progress_monitor.start('Restoring {0} references'.format(count), count)

    query.update(kind_hint=F('original_kind_hint'))

    #for reference in query.iterator():
        #reference.kind_hint = reference.original_kind_hint
        #reference.save()
        #progress_monitor.work(1)

    progress_monitor.done()


def recommend_filters(pname, bname, release, nofilter=False):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    if not nofilter:
        (simple_filters, _) = get_filters(codebase)
    else:
        simple_filters = []
    d = enchant.Dict('en-US')
    single_types = recommend_single_types(codebase, simple_filters, d)
    acronyms = recommend_acronyms(codebase, simple_filters)
    single_fields = recommend_single_fields(codebase, simple_filters)
    print_recommendations(single_types, acronyms, single_fields)


### ACTIONS USED BY OTHER ACTIONS ###

class LogEntry(object):
    def __init__(self):
        self.origin_size = 0
        self.final_size = 0
        self.custom_filtered = False
        self.filters = {}
        self.from_snippet = False
        self.unique_types = 0
        self.temp_types = []

    def compute_unique_types(self):
        types = set()
        for t in self.temp_types:
            index = t.rfind('.')
            types.add(t[:index])
        self.unique_types = len(types)


def analyze_all_logs(base_dir, project, version, source):
    analyze_class_log(base_dir, project, version, source)
    print()
    analyze_post_log(base_dir, project, version, source)
    print()
    analyze_method_log(base_dir, project, version, source)
    print()
    analyze_field_log(base_dir, project, version, source)


def analyze_post_log(base_dir, project, version, source):
    path = '{0}/linking-type-{1}-{2}-javapostclass-{3}.log'.format(base_dir,
            project, version, source)
    count = 0
    high_freq = 0
    depth = 0
    with codecs.open(path, 'r', 'utf-8') as finput:
        for line in finput:
            line = line.strip()
            if line.startswith('Type'):
                count += 1
            elif line == 'Rationale: highest_frequency':
                high_freq += 1
            elif line == 'Rationale: heuristic_depth':
                depth += 1

    print('Report for post-class')
    print('Count: {0}'.format(count))
    print('Filtered: {0}'.format(high_freq + depth))
    print('Heuristic depth: {0}'.format(depth))
    print('Highest Frequency: {0}'.format(high_freq))

def analyze_class_log(base_dir, project, version, source):
    files = [
            '{0}/linking-annotation-{1}-{2}-javaclass-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-enumeration-{1}-{2}-javaclass-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-class-{1}-{2}-javaclass-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-generic-class-{1}-{2}-javageneric-{3}.log'.format(base_dir,
                project, version, source),
            ]
    log_entries = process_log_files(files)
    log_stats(log_entries, 'class')


def analyze_method_log(base_dir, project, version, source):
    files = [
            '{0}/linking-method-{1}-{2}-javamethod-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-generic-method-{1}-{2}-javageneric-{3}.log'.format(base_dir,
                project, version, source),
            ]
    log_entries = process_log_files(files)
    log_stats(log_entries, 'method')


def analyze_field_log(base_dir, project, version, source):
    files = [
            '{0}/linking-annotation-field-{1}-{2}-javafield-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-enumeration value-{1}-{2}-javafield-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-field-{1}-{2}-javafield-{3}.log'.format(base_dir,
                project, version, source),
            '{0}/linking-generic-field-{1}-{2}-javageneric-{3}.log'.format(base_dir,
                project, version, source),
            ]
    log_entries = process_log_files(files)
    log_stats(log_entries, 'field')


def log_stats(log_entries, title):

    nonzero = 0
    filters = defaultdict(int)
    count = defaultdict(int)
    m = defaultdict(int)
    s = defaultdict(int)
    maxv = defaultdict(int)
    count0 = defaultdict(int)
    m0 = defaultdict(int)
    s0 = defaultdict(int)
    for log_entry in log_entries:
        if log_entry.origin_size > 0:
            nonzero += 1 
            # Original
            record_stat_entry(count, m, s, maxv, 'original',
                    log_entry.origin_size)
            record_stat_entry(count, m, s, maxv, 'finalsize',
                    log_entry.final_size)
            record_stat_entry(count, m, s, maxv, 'unique',
                    log_entry.unique_types)
            if log_entry.unique_types > 1 and log_entry.final_size > 0:
                count['hard'] += 1
            if log_entry.final_size > 0:
                count['linked'] += 1
            if log_entry.from_snippet:
                count['snippet'] += 1
            if log_entry.custom_filtered:
                count['custom'] += 1
            for filter in log_entry.filters:
                if log_entry.filters[filter][0]:
                    filters[filter] += 1
                else:
                    # To ensure that all filters are reported
                    filters[filter] += 0

        record_stat_entry(count0, m0, s0, None, 'original',
                log_entry.origin_size)
        if log_entry.from_snippet:
            count0['snippet'] += 1

    print('Report for {0}'.format(title))
    print('Number of code-like terms: {0}'.format(len(log_entries)))
    print('Number of code-like terms that matched at least one elem: {0}'
            .format(nonzero))
    print('Number of code-like terms linked: {0}'.format(count['linked']))
    print('Number of code-like terms difficult to link: {0}'.format(count['hard']))
    print('Number of code-like terms from snippets: {0}'
            .format(count['snippet']))
    print('Number of code-like terms from snippets with 0: {0}'
            .format(count0['snippet']))
    print('Number of code-like terms custom filtered: {0}'
            .format(count['custom']))
    print('Original size: {0}:{1}:{2}'.format(m['original'], sqrt(s['original']
        / float(max(1, count['original']))), maxv['original']))
    print('Original size with 0: {0}:{1}'.format(m0['original'],
        sqrt(s0['original'] / float(max(1, count0['original'])))))
    print('Final size: {0}:{1}:{2}'.format(m['finalsize'], sqrt(s['finalsize']
        / float(max(1, count['finalsize']))), maxv['finalsize']))
    print('Unique Types: {0}:{1}:{2}'.format(m['unique'], sqrt(s['unique']
        / float(max(1, count['unique']))), maxv['unique']))
    print('Filters:')
    for filter in filters:
        print('{0}: {1}'.format(filter, filters[filter]))
            
        # original
        # original no zero
        # final no zero
        # unique no zero
        # snippet
        # snippet no zero
        # custom no zero
        # filters: activated no zero

def record_stat_entry(count, m, s, maxv, key, val):
    count[key] += 1
    temp = m[key]
    m[key] += (val - temp) / float(count[key])
    s[key] += (val - temp) * (val - m[key])
    if maxv is not None:
        if val > maxv[key]:
            maxv[key] = val


def process_log_files(files):

    log_entries = []
    entry = None
    filtering = False
    visited = set()
    skip = False

    for f in files:
        if not os.path.exists(f):
            continue

        with codecs.open(f, 'r', 'utf-8') as finput:
            for line in finput:
                line = line.strip()
                size = len(line)
                if line.startswith('Type ') or line.startswith('Method ') or \
                    line.startswith('Field '):
                    filtering = False
                    if entry is not None and not skip:
                        entry.compute_unique_types()
                        log_entries.append(entry)
                    entry = LogEntry()
                    skip = False
                elif line.startswith('Original Size:'):
                    entry.origin_size = int(line[15:].strip())
                elif line.startswith('Final Size:'):
                    entry.final_size = int(line[12:].strip())
                elif line.startswith('Snippet'):
                    entry.from_snippet = line.find('True') > -1
                elif line.startswith('Custom Filtered'):
                    entry.custom_filtered = line.find('True') > -1
                elif line.startswith('Ref pk:'):
                    ref = line[8:]
                    if ref in visited:
                        skip = True
                    else:
                        visited.add(ref)
                elif line.startswith('Filtering'):
                    filtering = True
                elif line.startswith('Element:'):
                    filtering = False
                elif line.startswith('Original:'):
                    filtering = False
                    entry.temp_types.append(line[10:].strip())
                elif filtering and size > 0:
                    index = line.find(':')
                    if index < 0:
                        continue
                    name = line[:index].strip()
                    index2 = line.rfind('-')
                    activated = line[index:index2].find('True') > -1
                    number = int(line[index2+1:].strip())
                    entry.filters[name] = (activated, number)

        if entry is not None and not skip:
            log_entries.append(entry)
            entry = None
            filtering = False
        skip = False

    return log_entries


def recommend_single_types(codebase, simple_filters, d):
    single_types = set()
    types = CodeElement.objects.\
            filter(codebase=codebase).\
            filter(kind__is_type=True).\
            iterator()

    for element in types:
        simple_name = element.simple_name
        tokens = tokenize(simple_name)
        if len(tokens) == 1:
            lower = simple_name.lower()
            if lower not in simple_filters and d.check(lower):
                single_types.add(simple_name)

    return single_types


def recommend_acronyms(codebase, simple_filters):
    acronyms = set()
    types = CodeElement.objects.\
            filter(codebase=codebase).\
            filter(kind__is_type=True).\
            iterator()

    for element in types:
        simple_name = element.simple_name
        if simple_name.replace('_', '').isupper() and \
                simple_name.lower() not in simple_filters:
            acronyms.add(simple_name)

    return acronyms


def recommend_single_fields(codebase, simple_filters):
    single_fields = set()
    fields = CodeElement.objects.\
            filter(Q(kind__kind='field') |
                   Q(kind__kind='enumeration value') |
                   Q(kind__kind='annotation field')).iterator()

    for element in fields:
        simple_name = element.simple_name
        if simple_name.replace('_','a').isupper() and \
                simple_name.lower() not in simple_filters:
            single_fields.add(simple_name)

    return single_fields


def print_recommendations(single_types, acronyms, single_fields):
    print('FILTER RECOMMENDATIONS')
    print('\nSINGLE TYPE THAT LOOK LIKE WORDS')
    for single_type in single_types:
        print(single_type)
    print('\nSINGLE TYPES THAT LOOK LIKE ACRONYMS')
    for acronym in acronyms:
        print(acronym)
    print('\nFIELDS THAT LOOK LIKE ACRONYMS/WORDS')
    for single_field in single_fields:
        print(single_field)


def compute_f_ids(filtered_ids_path, filtered_ids_level):
    if filtered_ids_level is not None:
        if filtered_ids_level == 'g':
            f_level = 'global'
        else:
            f_level = 'local'
    else:
        f_level = None

    if filtered_ids_path is not None:
        f_ids = set()
        with codecs.open(filtered_ids_path, 'r', 'utf8') as f:
            for line in f:
                f_ids.add(int(line.strip()))
    else:
        f_ids = None

    return (f_ids, f_level)


def compute_filters(codebase):
    filters = CodeElementFilter.objects.filter(codebase=codebase).all()

    simple_filters = defaultdict(list)
    for cfilter in filters:
        simple_name = clean_java_name(cfilter.fqn)[0].lower()
        simple_filters[simple_name].append(cfilter)

    fqn_filters = {clean_java_name(cfilter.fqn.lower())[1]: cfilter
            for cfilter in filters}

    return (simple_filters, fqn_filters)


def get_filters(codebase):
    return get_value(PREFIX_CODEBASE_FILTERS,
        get_codebase_key(codebase),
        compute_filters,
        [codebase])


def get_package_name(tree):
    package_text = xtext(xpackage(tree)[0]).strip()
    return package_text[len('Package '):]


def compute_code_words(codebase):
    code_words = set()
    d = enchant.Dict('en-US')

    elements = CodeElement.objects.\
            filter(codebase=codebase).\
            filter(kind__is_type=True).\
            iterator()

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
    value = get_value(
            PREFIX_PROJECT_CODE_WORDS,
            project.pk,
            compute_project_code_words,
            [codebases]
            )
    return value


def get_default_kind_dict():
    kinds = {}
    kinds['unknown'] = CodeElementKind.objects.get(kind='unknown')
    kinds['class'] = CodeElementKind.objects.get(kind='class')
    kinds['annotation'] = CodeElementKind.objects.get(kind='annotation')
    kinds['method'] = CodeElementKind.objects.get(kind='method')
    kinds['field'] = CodeElementKind.objects.get(kind='field')
    kinds['xml element'] = CodeElementKind.objects.get(kind='xml element')
    kinds['xml attribute'] = CodeElementKind.objects.get(kind='xml attribute')
    kinds['xml attribute value'] = \
    CodeElementKind.objects.get(kind='xml attribute value')
    kinds['xml file'] = CodeElementKind.objects.get(kind='xml file')
    kinds['hbm file'] = CodeElementKind.objects.get(kind='hbm file')
    kinds['ini file'] = CodeElementKind.objects.get(kind='ini file')
    kinds['conf file'] = CodeElementKind.objects.get(kind='conf file')
    kinds['properties file'] = \
            CodeElementKind.objects.get(kind='properties file')
    kinds['log file'] = CodeElementKind.objects.get(kind='log file')
    kinds['jar file'] = CodeElementKind.objects.get(kind='jar file')
    kinds['java file'] = CodeElementKind.objects.get(kind='java file')
    kinds['python file'] = CodeElementKind.objects.get(kind='python file')
    return kinds


def get_java_strategies():
    strategies = [
            FileStrategy(), XMLStrategy(), ClassMethodStrategy(),
            MethodStrategy(), FieldStrategy(), AnnotationStrategy(),
            OtherStrategy(), IgnoreStrategy([EMAIL_PATTERN_RE, URL_PATTERN_RE])
            ]

    method_strategies = [ClassMethodStrategy(), MethodStrategy()]

    class_strategies = [AnnotationStrategy(), OtherStrategy()]

    kind_strategies = {
                'method': method_strategies,
                'class': class_strategies,
                'unknown': strategies
                }

    return kind_strategies


def get_default_filters():
    filters = {
        JAVA_LANGUAGE: [SQLFilter(), BuilderFilter(), MacroFilter()],
        XML_LANGUAGE: [],
        OTHER_LANGUAGE: [],
        }

    return filters


def classify_code_snippet(text, filters):
    code = None
    try:
        if is_xml_snippet(text)[0]:
            language = XML_LANGUAGE
        elif is_java_snippet(text, filters[JAVA_LANGUAGE])[0]:
            language = JAVA_LANGUAGE
        else:
            language = OTHER_LANGUAGE

        code = CodeSnippet(
                language=language,
                snippet_text=text,
                )
        code.save()
    except Exception:
        logger.exception('Error while classifying snippet.')
    return code


def parse_text_code_words(text, code_words):
    # Because there is a chance that the FQN will match...
    priority = 1
    matches = []
    words = split_pos(text)
    for (word, start, end) in words:
        if word in code_words:
            # Because at this stage, we force it to choose one only...
            matches.append(create_match((start, end, 'class', priority)))
    return matches


def process_children_matches(text, matches, children, index, single_refs,
        kinds, kinds_hierarchies, save_index, find_context):

    for i, child in enumerate(children):
        content = text[child[0]:child[1]]
        parent_reference = find_parent_reference(child[2], single_refs,
                        kinds_hierarchies)
        child_reference = SingleCodeReference(
                content=content,
                kind_hint=kinds[child[2]],
                original_kind_hint=kinds[child[2]],
                child_index=i,
                parent_reference=parent_reference)
        if save_index:
            child_reference.index = index
        if find_context:
            child_reference.sentence = find_sentence(text, child[0],
                    child[1])
            child_reference.paragraph = find_paragraph(text, child[0],
                    child[1])
        child_reference.save()
        single_refs.append(child_reference)


def process_matches(text, matches, single_refs, kinds, kinds_hierarchies,
        save_index, find_context, existing_refs):
    filtered = set()
    index = 0
    avoided = False

    for match in matches:
        if is_valid_match(match, matches, filtered):
            (parent, children) = match
            content = text[parent[0]:parent[1]]
            if parent[2] == IGNORE_KIND:
                avoided = True
                continue

            # This is a list of refs to avoid
            try:
                index = existing_refs.index(content)
                del(existing_refs[index])
                continue
            except ValueError:
                # That's ok, we can proceed!
                pass

            main_reference = SingleCodeReference(
                    content=content,
                    original_kind_hint=kinds[parent[2]],
                    kind_hint=kinds[parent[2]])
            #print('Main reference: {0}'.format(content))
            if save_index:
                main_reference.index = index
            if find_context:
                main_reference.sentence = find_sentence(text, parent[0],
                        parent[1])
                main_reference.paragraph = find_paragraph(text, parent[0],
                        parent[1])
            main_reference.save()
            #print('Main reference pk: {0}'.format(main_reference.pk))
            single_refs.append(main_reference)

            # Process children
            process_children_matches(text, matches, children, index,
                    single_refs, kinds, kinds_hierarchies, save_index,
                    find_context)
            index += 1
        else:
            filtered.add(match)

    return avoided


def parse_single_code_references(text, kind_hint, kind_strategies, kinds,
        kinds_hierarchies=ALL_KINDS_HIERARCHIES, save_index=False,
        strict=False, find_context=False, code_words=None, existing_refs=None):
    single_refs = []
    matches = []

    kind_text = kind_hint.kind
    if kind_text not in kind_strategies:
        kind_text = 'unknown'

    if existing_refs is None:
        existing_refs = []

    for strategy in kind_strategies[kind_text]:
        matches.extend(strategy.match(text))

    if code_words is not None:
        matches.extend(parse_text_code_words(text, code_words))

    # Sort to get correct indices
    matches.sort(key=lambda match: match[0][0])

    avoided = process_matches(text, matches, single_refs, kinds,
            kinds_hierarchies, save_index, find_context, existing_refs)

    if len(single_refs) == 0 and not avoided and not strict:
        code = SingleCodeReference(content=text, kind_hint=kind_hint,
                original_kind_hint=kind_hint)
        code.save()
        single_refs.append(code)

    return single_refs


def get_default_p_classifiers(include_stop=True):
    p_classifiers = []

    p_classifiers.append((is_empty_lines, REPLY_LANGUAGE))
    p_classifiers.append((is_reply_lines, REPLY_LANGUAGE))
    p_classifiers.append((is_reply_header, REPLY_LANGUAGE))
    if include_stop:
        p_classifiers.append((is_rest_reply, STOP_LANGUAGE))
    p_classifiers.append((
        partial(is_java_lines, filters=get_default_filters()[JAVA_LANGUAGE]),
        JAVA_LANGUAGE))
    p_classifiers.append((is_exception_trace_lines, JAVA_EXCEPTION_TRACE))
    p_classifiers.append((is_log_lines, LOG_LANGUAGE))
    p_classifiers.append((is_xml_lines, XML_LANGUAGE))

    return p_classifiers


def get_default_s_classifiers():
    s_classifiers = {}
    s_classifiers[JAVA_LANGUAGE] = can_merge_java

    return s_classifiers


def restore_original_kind(path, kind_str):
    kind = CodeElementKind.objects.get(kind=kind_str)
    with codecs.open(path, 'r', 'utf8') as f:
        for line in f:
            new_line = line.strip()
            if new_line.startswith('Ref pk:'):
                pk = int(new_line[8:].strip())
                ref = SingleCodeReference.objects.get(pk=pk)
                ref.original_kind_hint = kind
                ref.save()

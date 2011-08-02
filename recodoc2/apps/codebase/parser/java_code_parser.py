from __future__ import unicode_literals
from pydoc import deque
from threading import Thread
from Queue import Queue
import gc
import time
from traceback import print_exc
from django.db import connection
from py4j.java_gateway import JavaGateway
from py4j.protocol import Py4JJavaError
from codebase.models import CodeElementKind, CodeElement, MethodElement,\
        ParameterElement, FieldElement
from docutil.progress_monitor import NullProgressMonitor
from codeutil.java_element import clean_java_name

JAVA_PARSER = 'java'
PARSER_WORKER = 4
HIERARCHY_WORKER = 2


class HierarchyWorker(Thread):
    '''Worker that adds parents to code elements.'''

    def __init__(self, hierarchies, codebase, progress_monitor):
        '''
        :param hierarchies: queue of [child_fqn, parent_fqn, parent_fqn, ...]
        :param codebase:
        :param progress_monitor:
        '''
        Thread.__init__(self)
        self.hierarchies = hierarchies
        self.progress_monitor = progress_monitor
        self.codebase = codebase
        self.setDaemon(True)

    def run(self):
        while True:
            hierarchy = self.hierarchies.get()
            if hierarchy is None:
                # Sentinel value to indicate we are done!
                break
            child_fqn = hierarchy[0]
            child = CodeElement.objects.filter(codebase=self.codebase).\
                    get(fqn=child_fqn)
            for parent_fqn in hierarchy[1:]:
                try:
                    parent_element = CodeElement.objects.\
                            filter(codebase=self.codebase).get(fqn=parent_fqn)
                    child.parents.add(parent_element)
                except Exception:
                    # Not found!
                    # Probably because not in codebase!
                    pass
            self.progress_monitor.work('Parsed {0} hierarchy: {1} parents'.\
                    format(child_fqn, len(hierarchy) - 1))
            self.hierarchies.task_done()

        self.hierarchies.task_done()
        # Because django does not automatically close a connection created by
        # a custom thread...
        connection.close()


class CUWorker(Thread):
    '''Worker that processes a compilation unit'''

    def __init__(self, queue, codebase, hierarchies, gateway,
            progress_monitor):
        '''
        :param queue: queue of (cu, package_code_element, cu_name, work_amount)
                      where cu is a Java CompilationUnit.
        :param codebase:
        :param hierarchies: queue of [child_fqn, parent_fqn, parent_fqn, ...]
        :param gateway: Py4J gateway
        :param progress_monitor:
        '''
        Thread.__init__(self)
        self.setDaemon(True)
        self.queue = queue
        self.codebase = codebase
        # Does not work as expected because if a thread is waiting while being
        # a daemon and the last one, it seems that there may be glitches.
        #self.daemon = True
        self.hierarchies = hierarchies
        self.gateway = gateway
        self.progress_monitor = progress_monitor

        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.annotation_kind = CodeElementKind.objects.get(kind='annotation')
        self.enumeration_kind = CodeElementKind.objects.get(kind='enumeration')
        self.field_kind = CodeElementKind.objects.get(kind='field')
        self.method_kind = CodeElementKind.objects.get(kind='method')
        self.method_parameter_kind = CodeElementKind.objects.get(
                kind='method parameter')
        self.annotation_field_kind = CodeElementKind.objects.get(
                kind='annotation field')
        self.enumeration_value_kind = CodeElementKind.objects.get(
                kind='enumeration value')

        self.ASTParser = self.gateway.jvm.org.eclipse.jdt.core.dom.ASTParser
        self.JLS3 = self.gateway.jvm.org.eclipse.jdt.core.dom.AST.JLS3
        self.ast_parser = self.ASTParser.newParser(self.JLS3)
        self.IJavaElement = self.gateway.jvm.org.eclipse.jdt.core.IJavaElement
        self.Modifier = self.gateway.jvm.org.eclipse.jdt.core.dom.Modifier

    def _get_type_bindings(self, cunit):
        children = cunit.getChildren()
        new_types = []
        type_type = self.IJavaElement.TYPE
        for child in children:
            if child.getElementType() == type_type:
                new_types.append(child)

        array = self.gateway.new_array(self.IJavaElement, len(new_types))
        for i, type_element in enumerate(new_types):
            array[i] = type_element
        self.ast_parser.setSource(cunit)
        bindings = self.ast_parser.createBindings(array, None)
        return bindings

    def run(self):
        while True:
            item = self.queue.get()
            if item is None:
                # Sentinel value to indicate we are done.
                break
            (cu, package_code_element, cu_name, work_amount) = item
            self.progress_monitor.info('Parsing {0}'.format(cu_name))
            try:
                for type_binding in self._get_type_bindings(cu):
                    if type_binding is None:
                        # This is an anonymous class in a .class
                        continue
                    self._parse_type(type_binding, package_code_element)
            except Exception:
                print_exc()

            # Useful for Py4J
            gc.collect()
            self.queue.task_done()
            self.progress_monitor.work('Parsed {0}'.format(cu_name),
                    work_amount)

        self.queue.task_done()
        # Because django does not automatically close a connection created by
        # a custom thread...
        connection.close()

    def _parse_type(self, type_binding, container_code_element):
        if type_binding.isAnonymous():
            return
        java_element = type_binding.getJavaElement()
        (simple_name, fqn) = clean_java_name(type_binding.getQualifiedName())
        deprecated = type_binding.isDeprecated()

        abstract = self.Modifier.isAbstract(type_binding.getModifiers()) or \
            (type_binding.isInterface() and not type_binding.isAnnotation())

        type_code_element = CodeElement(codebase=self.codebase,
                simple_name=simple_name,
                fqn=fqn,
                eclipse_handle=java_element.getHandleIdentifier(),
                parser=JAVA_PARSER,
                deprecated=deprecated,
                abstract=abstract)
        type_code_element.binding = type_binding

        if type_binding.isAnnotation():
            type_code_element.kind = self.annotation_kind
        elif type_binding.isEnum():
            type_code_element.kind = self.enumeration_kind
        else:
            type_code_element.kind = self.class_kind
        type_code_element.save()
        type_code_element.containers.add(container_code_element)

        self._parse_type_members(type_binding, type_code_element)

        self._parse_type_hierarchy(type_binding, type_code_element)

    def _parse_type_members(self, type_binding, type_code_element):
        for method_binding in type_binding.getDeclaredMethods():
            if method_binding.isAnnotationMember():
                self._parse_annotation_field(method_binding, type_code_element)
            else:
                self._parse_method(method_binding, type_code_element)

        for field_binding in type_binding.getDeclaredFields():
            if field_binding.isEnumConstant():
                self._parse_enumeration_value(field_binding, type_code_element)
            else:
                self._parse_field(field_binding, type_code_element)

        for tbinding in type_binding.getDeclaredTypes():
            self._parse_type(tbinding, type_code_element)

    def _parse_type_hierarchy(self, type_binding, type_code_element):
        supertypes = [type_code_element.fqn]
        super_class = type_binding.getSuperclass()
        if super_class != None:
            (_, fqn) = clean_java_name(super_class.getQualifiedName())
            supertypes.append(fqn)

        for interface in type_binding.getInterfaces():
            (_, fqn) = clean_java_name(interface.getQualifiedName())
            supertypes.append(fqn)

        # Save hierarchy for further processing
        if len(supertypes) > 1:
            self.hierarchies.append(supertypes)

    def _parse_method(self, method_binding, container_code_element):
        # method header
        if self._is_private(method_binding):
            return

        java_element = method_binding.getJavaElement()
        if java_element is None:
            # This means that the method was inferred like default
            # constructor.
            # This is for compatibility with previous recodoc.
            return

        simple_name = method_binding.getName()
        (_, fqn) = clean_java_name(
                method_binding.getDeclaringClass().getQualifiedName())
        fqn = fqn + '.' + simple_name
        parameters = method_binding.getParameterTypes()
        try:
            parameter_names = java_element.getParameterNames()
        except Py4JJavaError:
            parameter_names = ["arg" for param in parameters]
        params_length = len(parameters)
        (return_simple_name, return_fqn) = clean_java_name(
                method_binding.getReturnType().getQualifiedName())
        deprecated = method_binding.isDeprecated()

        type_binding = container_code_element.binding
        abstract = self.Modifier.isAbstract(method_binding.getModifiers())\
                or (type_binding.isInterface() and
                    not type_binding.isAnnotation())

        method_code_element = MethodElement(codebase=self.codebase,
                kind=self.method_kind, simple_name=simple_name,
                fqn=fqn,
                parameters_length=params_length,
                eclipse_handle=java_element.getHandleIdentifier(),
                return_simple_name=return_simple_name,
                return_fqn=return_fqn,
                parser=JAVA_PARSER,
                deprecated=deprecated,
                abstract=abstract)

        # method container
        method_code_element.save()
        method_code_element.containers.add(container_code_element)

        # parse parameters
        for i, parameter in enumerate(parameters):
            (type_simple_name, type_fqn) = clean_java_name(
                    parameter.getQualifiedName())

            parameter_name = parameter_names[i]
            if parameter_name.startswith('arg'):
                parameter_name = ''
            simple_name = fqn = parameter_name

            parameter_code_element = ParameterElement(
                    codebase=self.codebase,
                    kind=self.method_parameter_kind,
                    simple_name=simple_name,
                    fqn=fqn,
                    type_simple_name=type_simple_name,
                    type_fqn=type_fqn,
                    index=i,
                    attcontainer=method_code_element,
                    parser=JAVA_PARSER)
            parameter_code_element.save()

        # If we ever need to get the deprecated replace
        # method.getJavadoc()
        # method.tags()
        # look for tag.getTagName() == 'deprecated'
        # look at subtag link or just plain text...

    def _is_private(self, binding):
        return self.Modifier.isPrivate(binding.getModifiers())

    def _parse_field(self, field_binding, container_code_element):
        if not self._is_private(field_binding):
            java_element = field_binding.getJavaElement()
            simple_name = field_binding.getName()
            (_, fqn) = clean_java_name(
                    field_binding.getDeclaringClass().getQualifiedName())
            fqn = fqn + '.' + simple_name
            (type_simple_name, type_fqn) = clean_java_name(
                    field_binding.getType().getQualifiedName())

            field_code_element = FieldElement(codebase=self.codebase,
                    kind=self.field_kind,
                    simple_name=simple_name,
                    fqn=fqn,
                    eclipse_handle=java_element.getHandleIdentifier(),
                    type_simple_name=type_simple_name,
                    type_fqn=type_fqn,
                    parser=JAVA_PARSER)
            field_code_element.save()
            field_code_element.containers.add(container_code_element)

    def _parse_enumeration_value(self, field_binding, container_code_element):
        if not self._is_private(field_binding):
            java_element = field_binding.getJavaElement()
            simple_name = field_binding.getName()
            (_, fqn) = clean_java_name(
                    field_binding.getDeclaringClass().getQualifiedName())
            fqn = fqn + '.' + simple_name
            (type_simple_name, type_fqn) = clean_java_name(
                    field_binding.getType().getQualifiedName())

            field_code_element = FieldElement(codebase=self.codebase,
                    kind=self.enumeration_value_kind,
                    simple_name=simple_name,
                    fqn=fqn,
                    eclipse_handle=java_element.getHandleIdentifier(),
                    type_simple_name=type_simple_name,
                    type_fqn=type_fqn,
                    parser=JAVA_PARSER)
            field_code_element.save()
            field_code_element.containers.add(container_code_element)

    def _parse_annotation_field(self, method_binding, container_code_element):
        if not self._is_private(method_binding):
            java_element = method_binding.getJavaElement()
            simple_name = method_binding.getName()
            (_, fqn) = clean_java_name(
                    method_binding.getDeclaringClass().getQualifiedName())
            fqn = fqn + '.' + simple_name
            (type_simple_name, type_fqn) = clean_java_name(
                    method_binding.getReturnType().getQualifiedName())

            field_code_element = FieldElement(codebase=self.codebase,
                    kind=self.annotation_field_kind,
                    simple_name=simple_name,
                    fqn=fqn,
                    eclipse_handle=java_element.getHandleIdentifier(),
                    type_simple_name=type_simple_name,
                    type_fqn=type_fqn,
                    attcontainer=container_code_element,
                    parser=JAVA_PARSER)
            field_code_element.save()
            field_code_element.containers.add(container_code_element)


class JavaParser(object):
    '''Parses a Java codebase and creates the appropriate CodeElement.

    This parser uses multiple threads to speed up the parsing. This parser
    requires access to Eclipse/Py4J'''

    JAVA_SRC_FOLDER = 'src'

    def __init__(self, codebase, project_key, opt_input):
        '''
        :param project_key: The name of the project in the Eclipse workspace.
        :param codebase: The codebase instance to which the CodeElement will
                         be associated with.
        :param opt_input: Optional input. Not used by this parser.
        '''
        self.project_name = project_key
        self.gateway = JavaGateway()

        self.hierarchies = deque()  # list of tuples. [(parent, child, child)]
        self.codebase = codebase
        self.queue = Queue()

        self.package_kind = CodeElementKind.objects.get(kind='package')

        if opt_input is None or opt_input.strip() == '' or opt_input == '-1':
            self.proot_name = None
            self.package_names = None
        else:
            inputs = opt_input.split(',')
            self.proot_name = inputs[0].strip()
            self.package_names = inputs[1:]

    def _get_package_root(self):
        ResourcePlugin = self.gateway.jvm.org.eclipse.core.resources.\
                ResourcesPlugin
        workspaceRoot = ResourcePlugin.getWorkspace().getRoot()
        project = workspaceRoot.getProject(self.project_name)
        java_project = self.gateway.jvm.org.eclipse.jdt.core.JavaCore.\
                create(project)
        if self.proot_name is None:
            src_folder = project.getFolder(JavaParser.JAVA_SRC_FOLDER)
            proot = java_project.getPackageFragmentRoot(src_folder)
        else:
            proot = None
            for temp_proot in java_project.getAllPackageFragmentRoots():
                if temp_proot.getElementName() == self.proot_name:
                    proot = temp_proot
                    break
        return proot

    def _should_filter_package(self, package_name):
        if self.package_names is None:
            return False
        else:
            should_keep = False
            for pname in self.package_names:
                if package_name.startswith(pname):
                    should_keep = True
                    break
            return not should_keep

    def _parse_packages(self, proot):
        packages = []
        for package in proot.getChildren():
            if package.hasChildren():
                package_name = package.getElementName()
                if self._should_filter_package(package_name):
                    continue
                package_code_element = CodeElement(codebase=self.codebase,
                        simple_name=package_name, fqn=package_name,
                        eclipse_handle=package.getHandleIdentifier(),
                        kind=self.package_kind, parser=JAVA_PARSER)
                package_code_element.save()
                packages.append((package, package_code_element))
        return packages

    def _need_class_files(self):
        return self.proot_name is not None and self.proot_name.endswith('.jar')

    def parse(self, progress_monitor=NullProgressMonitor()):
        '''Parses the codebase and creates CodeElement instances.

        :progress_monitor: A progress monitor to track the parsing progress.
        '''
        proot = self._get_package_root()
        packages = self._parse_packages(proot)
        progress_monitor.start('Parsing Java Project', len(packages))

        # Start workers:
        for _ in xrange(0, PARSER_WORKER):
            worker = CUWorker(self.queue, self.codebase, self.hierarchies,
                    self.gateway, progress_monitor)
            worker.start()

        start = time.time()
        for (package, package_code_element) in packages:
            gc.collect()  # for Py4J

            if self._need_class_files():
                cunits = package.getClassFiles()
            else:
                cunits = package.getCompilationUnits()

            unit_length = float(len(cunits))
            for cunit in cunits:
                cu_name = cunit.getElementName()
                if cu_name.find('$') > -1:
                    # Do not send internal classes: they will be parsed
                    # using type_binding.getDeclaredTypes()
                    continue

                winput = (cunit, package_code_element, cu_name,
                        1.0 / unit_length)
                self.queue.put(winput)

        for _ in xrange(0, PARSER_WORKER):
            self.queue.put(None)

        progress_monitor.info('Done parsing packages. Waiting for CUs.')
        self.queue.join()
        progress_monitor.done()
        self.gateway.close()
        print('Time: ' + str(time.time() - start))

        self.parse_hierarchy(progress_monitor)

    def parse_hierarchy(self, progress_monitor=NullProgressMonitor()):
        '''Builds the hierarchy of the parsed CodeElement instances.

        Must be called *after* parse.

        :param progress_monitor:
        '''
        queue = Queue()
        for hierarchy in self.hierarchies:
            queue.put(hierarchy)
        progress_monitor.start('Parsing Java Hierarchy', len(self.hierarchies))

        start = time.time()
        for _ in xrange(0, HIERARCHY_WORKER):
            # Sentinel value
            queue.put(None)
            worker = HierarchyWorker(queue, self.codebase, progress_monitor)
            worker.start()

        queue.join()
        progress_monitor.done()
        self.gateway.close()
        print('Time: ' + str(time.time() - start))

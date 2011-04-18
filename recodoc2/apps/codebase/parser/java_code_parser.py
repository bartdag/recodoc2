from __future__ import unicode_literals
from pydoc import deque
from threading import Thread
from Queue import Queue
import gc
import time
from traceback import print_exc
from django.db import connection
from py4j.java_gateway import JavaGateway
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

        self.ASTNode = self.gateway.jvm.org.eclipse.jdt.core.dom.ASTNode
        self.Modifier = self.gateway.jvm.org.eclipse.jdt.core.dom.Modifier
        self.type_type = self.ASTNode.TYPE_DECLARATION
        self.annotation_type = self.ASTNode.ANNOTATION_TYPE_DECLARATION
        self.enumeration_type = self.ASTNode.ENUM_DECLARATION
        self.method_type = self.ASTNode.METHOD_DECLARATION
        self.field_type = self.ASTNode.FIELD_DECLARATION
        #self.enumeration_value_type = self.ASTNode.ENUM_CONSTANT_DECLARATION
        self.annotation_field_type = \
                self.ASTNode.ANNOTATION_TYPE_MEMBER_DECLARATION

    def run(self):
        while True:
            item = self.queue.get()
            if item is None:
                # Sentinel value to indicate we are done.
                break
            (cu, package_code_element, cu_name, work_amount) = item
            self.progress_monitor.info('Parsing {0}'.format(cu_name))
            try:
                for jtype in cu.types():
                    self._parse_type(jtype, package_code_element)
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

    def _parse_type(self, jtype, container_code_element):
        type_binding = jtype.resolveBinding()
        java_element = type_binding.getJavaElement()
        (simple_name, fqn) = clean_java_name(type_binding.getQualifiedName())

        type_code_element = CodeElement(codebase=self.codebase,
                simple_name=simple_name,
                fqn=fqn,
                eclipse_handle=java_element.getHandleIdentifier(),
                parser=JAVA_PARSER)

        node_type = jtype.getNodeType()
        if node_type == self.annotation_type:
            type_code_element.kind = self.annotation_kind
        elif node_type == self.enumeration_type:
            type_code_element.kind = self.enumeration_kind
        else:
            type_code_element.kind = self.class_kind
        type_code_element.save()
        type_code_element.containers.add(container_code_element)

        self._parse_type_members(jtype, type_code_element)

        self._parse_type_hierarchy(jtype, type_binding, type_code_element)

    def _parse_type_members(self, jtype, type_code_element):
        for body_declaration in jtype.bodyDeclarations():
            node_type = body_declaration.getNodeType()
            if node_type == self.annotation_type or \
                    node_type == self.enumeration_type or \
                    node_type == self.type_type:
                self._parse_type(body_declaration, type_code_element)
            elif node_type == self.method_type:
                self._parse_method(body_declaration, type_code_element)
            elif node_type == self.field_type:
                self._parse_field(body_declaration, type_code_element)
            elif node_type == self.annotation_field_type:
                self._parse_annotation_field(body_declaration,
                        type_code_element)

        # Special case for enumerations...
        if type_code_element.kind == self.enumeration_kind:
            for body_declaration in jtype.enumConstants():
                self._parse_enumeration_value(body_declaration,
                        type_code_element)

    def _parse_type_hierarchy(self, jtype, type_binding, type_code_element):
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

    def _parse_method(self, method, container_code_element):
        # method header
        method_binding = method.resolveBinding()
        if not self._is_private(method_binding):
            java_element = method_binding.getJavaElement()
            simple_name = method_binding.getName()
            (_, fqn) = clean_java_name(
                    method_binding.getDeclaringClass().getQualifiedName())
            fqn = fqn + '.' + simple_name
            parameters = method_binding.getParameterTypes()
            parameter_declarations = method.parameters()
            params_length = len(parameters)
            (return_simple_name, return_fqn) = clean_java_name(
                    method_binding.getReturnType().getQualifiedName())
            method_code_element = MethodElement(codebase=self.codebase,
                    kind=self.method_kind, simple_name=simple_name,
                    fqn=fqn,
                    parameters_length=params_length,
                    eclipse_handle=java_element.getHandleIdentifier(),
                    return_simple_name=return_simple_name,
                    return_fqn=return_fqn,
                    parser=JAVA_PARSER)

            # method container
            method_code_element.save()
            method_code_element.containers.add(container_code_element)

            # parse parameters
            for i, parameter in enumerate(parameters):
                (type_simple_name, type_fqn) = clean_java_name(
                        parameter.getQualifiedName())
                simple_name = fqn = \
                        parameter_declarations[i].getName().getIdentifier()
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

    def _is_private(self, binding):
        return self.Modifier.isPrivate(binding.getModifiers())

    def _parse_field(self, field, container_code_element):
        for fragment in field.fragments():
            field_binding = fragment.resolveBinding()
            if not self._is_private(field_binding):
                java_element = field_binding.getJavaElement()
                simple_name = fragment.getName().getIdentifier()
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

    def _parse_enumeration_value(self, value, container_code_element):
        field_binding = value.resolveVariable()
        if not self._is_private(field_binding):
            java_element = field_binding.getJavaElement()
            simple_name = value.getName().getIdentifier()
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

    def _parse_annotation_field(self, field, container_code_element):
        method_binding = field.resolveBinding()
        if not self._is_private(method_binding):
            java_element = method_binding.getJavaElement()
            simple_name = field.getName().getIdentifier()
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
        self.ASTParser = self.gateway.jvm.org.eclipse.jdt.core.dom.ASTParser
        self.JLS3 = self.gateway.jvm.org.eclipse.jdt.core.dom.AST.JLS3

    def _get_package_root(self):
        ResourcePlugin = self.gateway.jvm.org.eclipse.core.resources.\
                ResourcesPlugin
        workspaceRoot = ResourcePlugin.getWorkspace().getRoot()
        project = workspaceRoot.getProject(self.project_name)
        java_project = self.gateway.jvm.org.eclipse.jdt.core.JavaCore.\
                create(project)
        src_folder = project.getFolder(JavaParser.JAVA_SRC_FOLDER)
        proot = java_project.getPackageFragmentRoot(src_folder)
        return proot

    def _parse_packages(self, proot):
        packages = []
        for package in proot.getChildren():
            if package.hasChildren():
                package_name = package.getElementName()
                package_code_element = CodeElement(codebase=self.codebase,
                        simple_name=package_name, fqn=package_name,
                        eclipse_handle=package.getHandleIdentifier(),
                        kind=self.package_kind, parser=JAVA_PARSER)
                package_code_element.save()
                packages.append((package, package_code_element))
        return packages

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
            cunits = package.getCompilationUnits()
            unit_length = float(len(cunits))
            for cunit in cunits:
                ast_parser = self.ASTParser.newParser(self.JLS3)
                ast_parser.setResolveBindings(True)
                ast_parser.setSource(cunit)
                cu = ast_parser.createAST(None)
                winput = (cu, package_code_element, cunit.getElementName(),
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

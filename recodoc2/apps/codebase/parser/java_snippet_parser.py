from __future__ import unicode_literals
import logging
import gc
from py4j.java_gateway import JavaGateway
from codebase.models import CodeElementKind, CodeSnippet, SingleCodeReference
from codeutil.java_element import is_cu_body, is_class_body
from docutil.progress_monitor import NullProgressMonitor
from traceback import print_exc


logger = logging.getLogger("recodoc.codebase.parser.java_snippet")


class JavaSnippetParser(object):

    HANDLE_SEPARATOR = ":"
    TYPE_KIND = "T"
    METHOD_KIND = "M"
    FIELD_KIND = "F"
    ANNOTATION_KIND = "A"
    ANNOTATION_PARAMETER_KIND = "P"
    ENUM_KIND = "E"
    ENUM_VALUE_KIND = "V"

    REQUEST_NAME = 'recodoc_request'

    def __init__(self, project, source):
        self.project = project
        self.source = source
        self._load()

    def _load(self):
        self.gateway = JavaGateway(start_callback_server=False)
        self.PPAUtil = self.gateway.jvm.ca.mcgill.cs.swevo.ppa.ui.PPAUtil
        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.unknown_kind = CodeElementKind.objects.get(kind='unknown')
        self.method_kind = CodeElementKind.objects.get(kind='method')
        self.field_kind = CodeElementKind.objects.get(kind='field')
        self.enumeration_kind = CodeElementKind.objects.get(kind='enumeration')
        self.annotation_kind = CodeElementKind.objects.get(kind='annotation')

    def parse(self, progress_monitor=NullProgressMonitor()):
        options = self.gateway.jvm.ca.mcgill.cs.swevo.ppa.PPAOptions()
        mcodes = CodeSnippet.objects.filter(language='j').\
                filter(project=self.project).\
                filter(source=self.source)

        #mcodes = CodeSnippet.objects.filter(pk=122170)
        count = mcodes.count()
        progress_monitor.start('Parsing Code Snippets ({0})'
                .format(count), count)

        for mcode in mcodes:

            # Don't parse snippets that are already parsed.
            if mcode.single_code_references.count() > 0:
                progress_monitor.word('Skipped a parsed code snippet', 1)
                continue

            text = mcode.snippet_text
            if text != None and text != '':
                try:
                    cu = self._get_cu(text, options)
                    if cu != None:
                        visitor = self.gateway.jvm.ca.mcgill.cs.swevo.ppa.ui.\
                                NameMapVisitor(True, True, True)
                        cu.accept(visitor)
                        self._process_name(
                                visitor.getBindings(),
                                visitor.getDeclarations(),
                                visitor.getNodes(),
                                mcode)
                except Exception:
                    logger.exception(
                            'Error with snippet: PK: {0}. Text:\n\n: {1}'
                            .format(mcode.pk, text))
                finally:
                    try:
                        self.PPAUtil.cleanUpAll(self.REQUEST_NAME)
                    except Exception:
                        print_exc()
            else:
                print('issue!')
            gc.collect()
            progress_monitor.work('Parsed a Code Snippet', 1)

        progress_monitor.done()
        self.gateway.close()

    def _get_cu(self, text, options):
        try:
            if is_cu_body(text):
                cu = self.PPAUtil.getCU(text, options, self.REQUEST_NAME)
            elif is_class_body(text):
                cu = self.PPAUtil.getSnippet(text, options, True,
                        self.REQUEST_NAME)
            else:
                cu = self.PPAUtil.getSnippet(text, options, False,
                        self.REQUEST_NAME)
        except Exception:
            cu = None
            logger.exception('Error while processing cu for {0}'.format(text))
        return cu

    def _process_name(self, bindings, declarations, nodes, mcode):
        for i, binding in enumerate(bindings):
            declaration = declarations[i]
            parts = binding.split(self.HANDLE_SEPARATOR)
            kind = parts[0][2]
            kind_hint = None
            content = binding
            if kind == self.TYPE_KIND:
                kind_hint = self.class_kind
            elif kind == self.METHOD_KIND:
                kind_hint = self.method_kind
            elif kind == self.FIELD_KIND:
                kind_hint = self.field_kind
            elif kind == self.ANNOTATION_KIND:
                kind_hint = self.annotation_kind
            elif kind == self.ENUM_KIND:
                kind_hint = self.enumeration_kind
            else:
                logger.warning('Not a high level code reference {0}'.\
                        format(kind))

            if kind_hint is not None:
                code = SingleCodeReference(
                        content=content,
                        xpath=mcode.xpath,
                        file_path=mcode.file_path,
                        kind_hint=kind_hint,
                        declaration=declaration,
                        snippet=mcode,
                        source=mcode.source,
                        index=(mcode.index * -1000) - i)
                code.project = self.project
                if hasattr(mcode, 'local_container'):
                    code.local_container = mcode.local_container
                if hasattr(mcode, 'mid_container'):
                    code.mid_container = mcode.mid_container
                if hasattr(mcode, 'global_container'):
                    code.global_container = mcode.global_container
                code.save()
from __future__ import unicode_literals
from doc.syncer.generic_syncer import GenericSyncer, SingleURLSyncer
from docutil.url_util import get_sanitized_url
import os

class JavadocSyncer(SingleURLSyncer):

    def _should_avoid(self, link):
        should_avoid = super(JavadocSyncer, self)._should_avoid(link)

        return should_avoid or\
                link.endswith('package-tree.html') or\
                link.endswith('overview-tree.html') or\
                link.endswith('package-use.html') or\
                link.endswith('deprecated-list.html') or\
                link.find('/index-files/') > -1 or\
                link.endswith('help-doc.html') or\
                link.endswith('allclasses-noframe.html') or\
                link.find('/class-use/') > -1 or\
                link.endswith('index.html') or\
                link.find('?') > -1 
                

class JavaJavadocSyncer(JavadocSyncer):

    def _should_avoid(self, link):
        should_avoid = super(JavaJavadocSyncer, self)._should_avoid(link)

        return should_avoid or\
                (link.find('docs/api/') > -1 and
                 link.find('docs/api/java/lang/') < 0)


class HtmlUnitSyncer(GenericSyncer):
    def __init__(self, input_url, output_url):
        input_url = get_sanitized_url(input_url)
        output_url = get_sanitized_url(output_url)
        scope = []
        base = os.path.split(input_url)[0]
        scope.append(base + '/gettingStarted.html')
        scope.append(base + '/keyboard-howto.html')
        scope.append(base + '/table-howto.html')
        scope.append(base + '/frame-howto.html')
        scope.append(base + '/window-howto.html')
        scope.append(base + '/javascript-howto.html')
        scope.append(base + '/activeX-howto.html')
        scope.append(base + '/logging.html')
        scope.append(base + '/faq.html')
        scope.append(base + '/index.html')

        super(HtmlUnitSyncer, self).__init__(
                input_urls=input_url,
                output_url=output_url,
                scope=scope)


class CommonsMathSyncer(GenericSyncer):
    def __init__(self, input_url, output_url):
        input_url = get_sanitized_url(input_url)
        output_url = get_sanitized_url(output_url)
        scope = []
        base = os.path.split(input_url)[0]
        scope.append(base + '/gettingStarted.html')
        scope.append(base + '/keyboard-howto.html')
        scope.append(base + '/table-howto.html')
        scope.append(base + '/frame-howto.html')
        scope.append(base + '/window-howto.html')
        scope.append(base + '/javascript-howto.html')
        scope.append(base + '/activeX-howto.html')
        scope.append(base + '/logging.html')
        scope.append(base + '/faq.html')
        scope.append(base + '/index.html')

        super(HtmlUnitSyncer, self).__init__(
                input_urls=input_url,
                output_url=output_url,
                scope=scope)


class XStreamSyncer(GenericSyncer):
    def __init__(self, input_url, output_url):

        input_url = get_sanitized_url(input_url)
        output_url = get_sanitized_url(output_url)

        if input_url.endswith('/'):
            scope_url = input_url
        else:
            (scope_url, _) = os.path.split(input_url)
            scope_url += '/'
        scope = [scope_url]
        input_urls = [input_url]
        input_urls.append(scope_url + 'alias-tutorial.html')
        input_urls.append(scope_url + 'annotations-tutorial.html')
        input_urls.append(scope_url + 'architecture.html')
        input_urls.append(scope_url + 'changes.html')
        input_urls.append(scope_url + 'converter-tutorial.html')
        input_urls.append(scope_url + 'converters.html')
        input_urls.append(scope_url + 'download.html')
        input_urls.append(scope_url + 'faq.html')
        input_urls.append(scope_url + 'graphs.html')
        input_urls.append(scope_url + 'how-to-contribute.html')
        input_urls.append(scope_url + 'index.html')
        input_urls.append(scope_url + 'json-tutorial.html')
        input_urls.append(scope_url + 'license.html')
        input_urls.append(scope_url + 'list-dev.html')
        input_urls.append(scope_url + 'list-user.html')
        input_urls.append(scope_url + 'manual-tweaking-output.html')
        input_urls.append(scope_url + 'manual.html')
        input_urls.append(scope_url + 'news.html')
        input_urls.append(scope_url + 'objectstream.html')
        input_urls.append(scope_url + 'persistence-tutorial.html')
        input_urls.append(scope_url + 'references.html')
        input_urls.append(scope_url + 'repository.html')
        input_urls.append(scope_url + 'team.html')
        input_urls.append(scope_url + 'tutorial.html')
        input_urls.append(scope_url + 'versioning.html')
        
        GenericSyncer.logger.debug('SCOPE: {0}'.format(scope_url))

        super(XStreamSyncer, self).__init__(
                input_urls=input_urls,
                output_url=output_url,
                scope=scope)

    def _should_avoid(self, link):
        should_avoid = super(XStreamSyncer, self)._should_avoid(link)
        if not should_avoid:
            should_avoid = link.find('javadoc') > -1
        return should_avoid

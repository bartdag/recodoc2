from __future__ import unicode_literals
from doc.syncer.generic_syncer import GenericSyncer, SingleURLSyncer
from docutil.url_util import get_sanitized_url
import os


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


class XStreamSyncer(SingleURLSyncer):
    def __init__(self, input_url, output_url):

        super(XStreamSyncer, self).__init__(
                input_url=input_url,
                output_url=output_url,
                )

    def _should_avoid(self, link):
        should_avoid = super(XStreamSyncer, self)._should_avoid(link)
        if not should_avoid:
            should_avoid = link.find('javadoc') > -1
        return should_avoid

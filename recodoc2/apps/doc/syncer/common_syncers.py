from __future__ import unicode_literals
from doc.syncer.generic_syncer import GenericSyncer
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


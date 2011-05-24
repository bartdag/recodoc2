from __future__ import unicode_literals
import os.path
import urlparse
import urllib
import httplib
from django.conf import settings


FILE_PROTOCOL = 'file://'
SOURCE_FILE_EXT = ['.html', '.htm', '.jsp', '.php']
HASH = '#'
QUERY = '?'
ROOT = '__root.html'
ROOT_ROOT = 'root__root.html'


def check_url(host, request, https=False):
    try:
        if https:
            conn = httplib.HTTPSConnection(host)
            conn.request('HEAD', request)
            res = conn.getresponse()
            conn.close()
        else:
            conn = httplib.HTTPConnection(host)
            conn.request('HEAD', request)
            res = conn.getresponse()
            conn.close()

        return res.status == 200
    except Exception:
        return False


def sanitize_file_name(file_name, escape='--'):
    '''Removes characters that cause path problem in windows/linux'''
    return file_name.replace('!', escape).replace('/', escape)


def get_relative_url(url, base=settings.PROJECT_FS_ROOT):
    '''Given a base and a url, return the relative url from the base'''
    new_base = base
    if not base.endswith('/'):
        new_base += '/'

    index = url.find(new_base)
    if index > -1:
        return url[index + len(new_base):]
    else:
        return url


def is_local(url):
    scheme = urlparse.urlparse(url).scheme
    return scheme == '' or scheme == 'file'


def is_absolute(url):
    scheme = urlparse.urlparse(url).scheme
    return scheme != '' or os.path.isabs(url)


def get_url_without_hash(url):
    new_url = url
    index = url.rfind(HASH)
    if index > 0:
        new_url = url[0:index]
    return new_url


def get_path(url):
    return urlparse.urlparse(url).path


def get_sanitized_file(url):
    (_, afile) = os.path.split(url)
    index = afile.find(HASH)
    if index > -1:
        afile = afile[:index]

    index = afile.find(QUERY)
    if index > -1:
        afile = afile[:index]

    return afile


def get_sanitized_url(url):
    good_url = url
    if is_absolute(url) and urlparse.urlparse(url).scheme == '':
        good_url = FILE_PROTOCOL + good_url
    return good_url


def get_sanitized_directory(url):
    sanitized_url = url
    if not url.endswith(os.sep):
        sanitized_url = sanitized_url + os.sep
    return sanitized_url


def create_intermediate_path(directory):
    if directory is None:
        raise Exception('dir is None')
    if not os.path.exists(directory):
        parent = os.path.dirname(directory)
        if not os.path.exists(parent):
            create_intermediate_path(parent)
        os.mkdir(directory)


def ensure_path_exists(url):
    path = urlparse.urlparse(url).path
    directory = os.path.dirname(path)
    create_intermediate_path(directory)


def is_source_file(url):
    afile = get_sanitized_file(url)
    (_, ext) = os.path.splitext(afile)

    return ext in SOURCE_FILE_EXT


def get_path_from_url(url_or_path):
    return urlparse.urlparse(url_or_path).path


def get_local_url(base_url, url):
    '''Merges base_url and url:
       Take the path of url and append it to base_url'''

    if not base_url:
        return url

    base_url = get_sanitized_directory(base_url)
    url_path = urlparse.urlparse(url).path[1:]

    destination_url = urlparse.urljoin(base_url, url_path)
    (_, ext) = os.path.splitext(destination_url)

    if ext == '':
        url_path = get_sanitized_directory(url_path)
        destination_url = get_sanitized_directory(destination_url)
        if (url_path == os.sep):
            destination_url = urlparse.urljoin(destination_url, ROOT_ROOT)
        else:
            root_page = os.path.basename(os.path.dirname(url_path)) + ROOT
            destination_url = urlparse.urljoin(destination_url, root_page)

    return destination_url


def replace_space(url, lowerize=False):
    new_url = url.replace(' ', '_')
    if lowerize:
        new_url = new_url.lower()
    return new_url


def get_safe_local_id(url, index='', suffix='.html'):
    parse_result = urlparse.urlparse(url)
    last_path = os.path.split(parse_result.path)[1]

    # This is the case where the url ends with a slash...
    # We remove the slash and get the last bit, probably a uid by itself.
    if last_path == '':
        url_path = parse_result.path[:-1]
        last_path = os.path.split(url_path)[1]

    uid = last_path + '?' + parse_result.query + index + suffix
    uid = urllib.quote_plus(uid)
    return uid

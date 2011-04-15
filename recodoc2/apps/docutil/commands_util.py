from __future__ import unicode_literals
import cPickle
import os
import time
import random
import urllib2
import logging
import shutil
import codecs
import chardet
from itertools import izip_longest
from django.db import transaction
from django.conf import settings

from project.models import RecoDocError
from docutil.url_util import get_sanitized_url, is_local

USER_AGENTS = ["Mozilla/5.0 (X11; U; Linux i686; ru; rv:1.9.3a5pre) Gecko/20100526 Firefox/3.7a5pre",
               "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)",
               "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.5) Gecko/20091109 Ubuntu/9.10 (karmic) Firefox/3.5.5",
               "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3) Gecko/20091010 Iceweasel/3.5.3 (Debian-3.5.3-2)",
               "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Win64; x64; Trident/4.0; .NET CLR 2.0.50727; SLCC2; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET CLR 3.0.04506; Media Center PC 5.0; SLCC1)",
               "Opera/9.99 (Windows NT 5.1; U; pl) Presto/9.9.9",
               "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_4; en-gb) AppleWebKit/528.4+ (KHTML, like Gecko) Version/4.0dp1 Safari/526.11.2",
               "Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.1) Gecko/20090624 Firefox/3.5"]

REFERERS = ["http://www.google.com", "http://www.yahoo.com", "http://www.bing.com"]

MAX_DOWNLOAD_RETRY = 2
MODEL_FILE = 'model.pkl'

logger = logging.getLogger("recodoc.docutil.commands_util")


def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
    into well-behaved decorators, so long as the decorators
    are fairly simple. If a decorator expects a function and
    returns a function (no descriptors), and if it doesn't
    modify function attributes or docstring, then it is
    eligible to use this. Simply apply @simple_decorator to
    your decorator and it will automatically preserve the
    docstring and function attributes of functions to which
    it is applied."""
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator


def mkdir_safe(path):
    '''Creates a directory if it does not already exist'''
    if not os.path.exists(path):
        os.mkdir(path)


def import_clazz(fqn):
    '''Returns a class specified by the fully qualified name. For example:
       foo.baz.MyClass'''
    clazz = None
    index = fqn.rfind('.')
    if index != -1:
        clazz_name = fqn[index + 1:]
        mod = __import__(fqn[:index], globals(), locals(), [clazz_name])
        clazz = getattr(mod, clazz_name)
    return clazz


@simple_decorator
def recocommand(f):
    def newf(*args, **kargs):
        start = time.clock()
        transaction.enter_transaction_management()
        transaction.managed(True)
        return_value = f(*args, **kargs)

        # In case somebody forgot to commit... wow...
        transaction.commit()
        transaction.leave_transaction_management()
        stop = time.clock()
        print('Command time: {0}'.format(stop - start))
        return return_value
    return newf


def load_model(pname, intermediate_path, key):
    basepath = settings.PROJECT_FS_ROOT
    path = os.path.join(basepath, pname, intermediate_path, key)
    model_file_path = os.path.join(path, MODEL_FILE)
    with open(model_file_path, 'rb') as model_file:
        model = cPickle.load(model_file)
    return model


def dump_model(model, pname, intermediate_path, key):
    basepath = settings.PROJECT_FS_ROOT
    path = os.path.join(basepath, pname, intermediate_path, key)
    model_file_path = os.path.join(path, MODEL_FILE)
    with open(model_file_path, 'wb') as model_file:
        cPickle.dump(model, model_file, -1)


def get_file_from(url):
    trial = 0
    file_from = None
    while trial < MAX_DOWNLOAD_RETRY:
        try:
            file_from = urllib2.urlopen(url)
            break
        except:
            # Do not wait for local url.
            if is_local(url):
                break
            else:
                trial += 1
                time.sleep(1)

    if file_from == None:
        logger.exception('Error happened while opening url {0}'.format(url))
        raise RecoDocError('Error downloading {0}'.format(url))
    elif trial > 0:
        print('At least it was worth it')

    return file_from


def get_cookie():
    cookie_str = ''
    try:
        cookie_str = settings.CURRENT_COOKIE
    except Exception:
        cookie_str = ''
    return cookie_str


def get_file_from_real_browser(url):
    trial = 0
    file_from = None
    agent = random.choice(USER_AGENTS)
    referer = random.choice(REFERERS)
    wait_time = random.uniform(4, 9)
    time.sleep(wait_time)
    cookie_str = get_cookie()
    while trial < 2:
        try:
            hdrs = {'User-Agent':  agent,
                    'Referer': referer,
                    'Connection': 'keep-alive',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Keep-Alive': '115',
                    'Cookie': cookie_str,
                    }
            req = urllib2.Request(url, headers=hdrs)
            print('Making a request {0}\nwith cookie:\n{1}'.format(
                url, cookie_str))
            file_from = urllib2.urlopen(req)
            break
        except Exception:
            trial += 1
            time.sleep(1)

    if file_from == None:
        logger.exception('Error happened while opening url {0}'.format(url))
        raise RecoDocError('Error downloading {0}'.format(url))
    elif trial > 0:
        print('At least it was worth it')

    return file_from


def get_encoding(content):
    encodings = chardet.detect(content)
    if 'encoding' in encodings:
        return encodings['encoding']
    else:
        return 'utf8'


def download_file(file_from_path, file_to_path, force=False, binary=False,
        real_browser=False):
    url = get_sanitized_url(file_from_path)

    if os.path.exists(file_to_path) and \
       os.path.getsize(file_to_path) > 0 and \
       not force:
        logger.info('Skipped downloading {0} because it already exists in '
                '{1}'.format(url, file_to_path))
        return
    try:
        if not real_browser:
            file_from = get_file_from(url)
        else:
            file_from = get_file_from_real_browser(url)

        if binary:
            file_to = open(file_to_path, 'wb')
        else:
            file_to = codecs.open(file_to_path, 'w', encoding='utf8')

        logger.info('Downloading {0} to {1} in mode binary? {2}'.format(url,
            file_to_path, binary))
        if not binary:
            content = file_from.read()
            encoding = get_encoding(content)
            content = unicode(content, encoding)
            file_to.write(content)
            file_from.close()
            file_to.close()
        else:
            shutil.copyfileobj(file_from, file_to)
    except:
        logger.exception('Error while downloading a file: {0}'.format(
            url))
        if os.path.exists(file_to_path):
            os.remove(file_to_path)
        raise RecoDocError('Error downloading {0}'.format(url))


def chunk_it(l, chunks):
    return list(zip(*izip_longest(*[iter(l)]*chunks)))

from __future__ import unicode_literals
import hashlib
from traceback import print_exc
from django.core.cache import cache
from docutil.str_util import smart_decode, normalize

DEFAULT_EXPIRED = '!hasxpired_'
DEFAULT_EXPIRATION_TIME = 3600

cache_total = cache_miss = 0


def reset_cache_stats():
    global cache_total
    global cache_miss
    cache_total = 0
    cache_miss = 0


def clear_cache():
    cache.clear()


def get_value(prefix, key, cache_function, args=None,
        expiration=DEFAULT_EXPIRATION_TIME):
    '''Please note that even if CACHE_MIDDLEWARE_KEY_PREFIX is set in
       settings, the prefix is not appended to the key when manually
       using the cache so a prefix is required.
    '''
    global cache_total
    global cache_miss

    new_key = get_safe_key(smart_decode(prefix) + smart_decode(key))
    try:
        value = cache.get(new_key, DEFAULT_EXPIRED)
    except Exception:
        value = DEFAULT_EXPIRED
        print_exc()
    cache_total += 1
    if value == DEFAULT_EXPIRED:
        cache_miss += 1
        if args is None:
            value = cache_function()
        else:
            value = cache_function(*args)
        cache.set(new_key, value, expiration)
    return value


def set_value(prefix, key, value, expiration=DEFAULT_EXPIRATION_TIME):
    new_key = get_safe_key(smart_decode(prefix) + smart_decode(key))
    cache.set(new_key, value, expiration)


def get_safe_key(key):
    m = hashlib.md5()
    new_key = normalize(smart_decode(key))
    m.update(new_key.encode('utf8'))
    return m.hexdigest()


def get_codebase_key(codebase):
    return ''.join([
            codebase.project_release.project.name,
            codebase.project_release.release,
            codebase.name])

# Django settings for recodoc2 project.
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.append(os.path.join(HERE, 'apps'))


#DEBUG = False
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
        ('Name', 'admin@admin.com'),
)

MANAGERS = ADMINS

CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'recodoc2-main',
            }
        }

CACHE_MIDDLEWARE_ALIAS = 'default'

CACHE_MIDDLEWARE_SECONDS = 600

CACHE_MIDDLEWARE_KEY_PREFIX = 'rec2'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Montreal'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = os.path.normpath(os.path.join(HERE, '../static/'))

TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(HERE, '../templates')),
)

STATICFILES_DIRS = (
        os.path.join(HERE, 'static'),
)

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'abcdefghijklmnop'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'recodoc2.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'devserver',
    'docutil',
    'codeutil',
    'project',
    'codebase',
    'doc',
    'channel',
    'linkertest',
    'recommender',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# RECODOC SETTINGS

TESTDATA = os.path.join(HERE, 'testdata')

CODE_PARSERS = {'java': 'codebase.parser.java_code_parser.JavaParser',
                'xsd': '',
                'dtd': ''}

CUSTOM_CODE_PARSERS = {}

CODE_SNIPPET_PARSERS = {
            'java': 'codebase.parser.java_snippet_parser.JavaSnippetParser',
            'xml': '',
            }

CUSTOM_CODE_SNIPPET_PARSERS = {}

LINKERS = {'javaclass': 'codebase.linker.java_linkers.JavaClassLinker',
           'javapostclass': 'codebase.linker.java_linkers.JavaPostClassLinker',
           'javamethod': 'codebase.linker.java_linkers.JavaMethodLinker',
           'javafield': 'codebase.linker.java_linkers.JavaFieldLinker',
           'javageneric': 'codebase.linker.java_linkers.JavaGenericLinker', }

CUSTOM_LINKERS = {}

CHANNEL_LINE_THRESHOLD = 500

# Not supported yet
#SAVE_THREAD_TEXT = False
# Not supported yet
#SAVE_PAGE_TEXT = False

SAVE_MESSAGE_TEXT = False
SAVE_SECTION_TEXT = False

DEVSERVER_MODULES = (
    #'devserver.modules.sql.SQLRealTimeModule',
    #'devserver.modules.sql.SQLSummaryModule',
    #'devserver.modules.profile.ProfileSummaryModule',

    # Modules not enabled by default
    #'devserver.modules.ajax.AjaxDumpModule',
    #'devserver.modules.profile.MemoryUseModule',
    #'devserver.modules.cache.CacheSummaryModule',
    #'devserver.modules.profile.LineProfilerModule',
)

try:
    from localsettings import *
except Exception:
    raise Exception('Local settings not loaded!')

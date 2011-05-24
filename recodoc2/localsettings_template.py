# Local Settings Template.
# Rename this template to localsettings.py. The file should be located in the
# same directory as settings.py.

# **Step 1. Configure database access**
# Only change NAME if you want to use sqlite3.
# For better performance, PostgreSQL is recommended.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/path/to/db',                  # Name of DB or sqlite3 path.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}



# **Step 2. Configure Cache**
# Uncomment the following lines if you have installed (and started) memcached.
#CACHES = {
        #'default': {
            #'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            #'LOCATION': '127.0.0.1:11211'
            #},
#}


# **Step 3. Configure Paths**

# This is the path where files will be downloaded (e.g., mailing list messages,
# documentation pages, etc.).
PROJECT_FS_ROOT = ('/path/to/recodoc_data')

# This is a path were test files will be downloaded for unit test. This path
# MUST be different than PROJECT_FS_ROOT because it is frequently erased by the
# unit tests.
PROJECT_FS_ROOT_TEST = ('/path/to/recodoc_test_data')

# This is a path were test files will be downloaded for unit test. Yes, we need
# a second path.
PROJECT_FS_ROOT_TEST2 = ('/path/to/recodoc_test_data2')

# This is the path to run the Eclipse instance where PPA and Py4J are
# installed. Required for Java code analysis, snippet parsing, and linking.
ECLIPSE_COMMAND = ('/home/barthelemy/eclipse_prog/eclipse_doc2/eclipse')


# **Step 4. Enter a secret key**
# You can generate a key at this address: http://www.miniwebtool.com/django-secret-key-generator/
SECRET_KEY = 'secret-key'

# **Step 5. Configure Admin info**
# This is not really used, but you should add your name and email here.
ADMINS = (
        ('Name', 'email@example.com'),
)

# **Step 6. Test Runner**
# If you have installed django-test-coverage, uncomment the following line
# to generate coverage report when running unit tests.
#TEST_RUNNER = 'django-test-coverage.runner.run_tests'


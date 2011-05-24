Recodoc - Documentation Analyzer and Recommender
================================================

:Authors:
  Barthelemy Dagenais
:Version: 0.1

Recodoc is a set of tools to analyze developer documentation, mailing lists, and
codebases and recommend improvements to the documentation. It is highly
modularized and extensible so only parts of recodoc can be used (e.g., the
mailing list crawler).

Recodoc is mainly used through the command line. Users can navigate the data
model using the web admin interface. News formats of documentation and mailing
lists are added by writing Python classes that extend the existing
documentation and mailing list parsers and crawlers.

Because Recodoc is fairly involved (it is a mix of web crawler, parser, screen
scraping, knowledge modelling, partial code compilation, natural language
processing, analytics, recommendation system), the installation instructions
are more complex than your typical developer tool. This document assumes that
the users are familiar with Python and to a certain extent, Java.

Recodoc is built on `Django <http://www.djangoproject.com/>`_, a web framework
and ORM for Python. Recodoc also extensively uses `lxml <http://lxml.de/>`_, an
xml processing library, the Eclipse Java compiler, `Partial Program Analysis
for Java <http://www.sable.mcgill.ca/ppa/ppa_eclipse.html>`_, and `Py4J
<http://py4j.sourceforge.net/>`_.

.. contents:: Contents
   :backlinks: top


Features
--------

Code Analysis
~~~~~~~~~~~~~

Java parsing
  Parses an Eclipse Java project and creates a model of the code:
  packages, classes, methods, fields, parameters. Declaration and hierarchy
  relationships between these *code elements* are captured in the model.

XML parsing
  Parses a DTD or a schema (.xsd) file and creates a corresponding model. *The
  code is not ported yet to this new version.*


Documentation Analysis
~~~~~~~~~~~~~~~~~~~~~~

crawling
  Given a URL, downloads all the documentation pages of an HTML document.

parsing
  Parses a document and creates a model: sections, pages, code-like terms,
  code snippets.


Support Channel Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

crawling
  Given a URL to a forum or a mailing list archive, downloads all the messages.

parsing
  Parses a support channel archive and creates a model: support threads,
  messages, code-like terms, code snippets.


Code-like Terms and Snippets Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

snippet classification
  Classifies code snippets into the following categories: Java code snippet,
  Java exception stack trace, XML snippet, log trace.

snippet parsing
  Compiles Java code snippets to resolve and infer missing types. Parses
  snippets (Java and XML) to extract a list of code-like terms.

code-like terms classification
  Classifies code-like terms into likely code element kind. For example, the
  word ``FooBar`` is classified as a ``class``.


Model Linking
~~~~~~~~~~~~~

Java model linking
  Links Java codebases with Java code-like terms found in documentation and support
  channels.

XML model linking
  Links XML model with xml code-like terms found in documentation and support
  channels. *The code is not ported yet to this new version.*
  

Documentation Improvements Recommendation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is currently being implemented.


Requirements
------------

This is a list of libraries and programs that need to be installed and
configured prior to install Recodoc. All of the other dependencies are covered
in the Installation section.


General Requirements
~~~~~~~~~~~~~~~~~~~~

* Python 2.7 (Python 2.6 or 3.0+ will not work).
* PostgreSQL(>=8.4), MySQL (>=5.0.3), or Oracle. *Note: sqlite will not work
  because Recodoc uses multiple processes to speed up the parsers and sqlite
  does not like that.*

Please note that PostgreSQL is strongly recommended because it has less
limitations than MySQL and the default configuration is better for Recodoc
needs. Recodoc was developed with PostgreSQL, and lightly tested with MySQL.

If you do not have experience configuring PostgreSQL or MySQL, you can use one
of their useful GUI tools: `pgAdmin <http://www.pgadmin.org/>`_ and `MySQL
Workbench <http://wb.mysql.com/>`_.


Requirements for Code Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These libraries and programs are required to analyze Java codebases. Analyzing
Java codebases is a prerequisite for Java snippet parsing, model linking,
documentation improvements recommendation. If you plan to only use Support
Channel or Documentation Analysis, you do not need these libraries and
programs.

* Java 1.6
* Eclipse 3.6


Optional Requirements
~~~~~~~~~~~~~~~~~~~~~

These libraries and programs should be installed to improve the performance and
the usage/maintenance of Recodoc:

* memcached
* virtualenv
* ipython (for interacting with the model through a Python shell)


Installation
------------

This section assumes that you are familiar with Python and virtualenv. The
following code snippets will walk you through the installation of Recodoc and
of its dependencies. The steps assume a Linux environment under a bash shell.

Step 1. Create a virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We assume that you want to install the dependencies in a virtual environment.
If you want to install the dependencies globally, skip this step.

::

  cd $HOME
  mkdir .virtualenvs
  virtualenv --no-site-package --distribute .virtualenvs/recodoc2

  # The following step will activate the virtual environment.
  # It is assumed that the next steps are performed while
  # the environment is activated.
  source .virtualenvs/recodoc2/bin/activate


Step 2. Install the required dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  
  pip install django
  pip install lxml
  pip install pyenchant
  pip install Py4J
  pip install chardet

  # For MySQL
  pip install MySQL-python

  # For PostgreSQL (requires gcc. otherwise download the binary)
  pip install psycopg2

If you want to install pyscopg2 without compiling it (e.g., on windows),
download the `binary package <http://www.initd.org/psycopg/download/>`_.


Step 3. Install the optional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These dependencies are only required if you want to analyze Java code. First,
install the following Python libraries:

::

  # This is for memcached
  pip install pylibmc

  # This is for the advanced Python shell
  pip install ipython

Then, install Py4J in Eclipse using the following update site:
``http://py4j.sourceforge.net/py4j_eclipse``.

Finally, install PPA in Eclipse using the following update site:
``http://www.sable.mcgill.ca/ppa/site_1.2.x``.

Since PPA is updated frequently but not released often, you might be better
downloading it and building the update site locally. The source code is
`located on bitbucket <https://bitbucket.org/barthe/ppa/wiki/Home>`_.  

Step 4. Install the development dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to contribute to Recodoc, install the following Python programs:

::

  pip install gitli
  pip install coverage
  pip install django-test-coverage
  pip install sphinx


Step 5. Download Recodoc
~~~~~~~~~~~~~~~~~~~~~~~~

First, clone the Recodoc git repository.

::

  cd $HOME
  mkdir projects
  cd projects
  git clone -b develop git@github.com:bartdag/recodoc2.git


Then, copy and edit the localsettings file. The file is heavily commented and
there are only a few steps to follow.

::

  cd recodoc2/recodoc2
  cp localsettings_template.py localsettings.py
  vim localsettings.py

Initialize the database by running the following command and creating an admin
user (one index might fail to install if you use MySQL):

::

  ./manage.py syncdb

  # Alternatively, if manage.py does not have execution permission:
  python manage.py syncdb


Finally, run one of the following unit tests to ensure that everything was
installed correctly. These tests do not require Eclipse/Java.

::

  # Test Documentation Analysis.
  ./manage.py test doc

  # Test Support Channel Analysis. Can take 30 seconds.
  ./manage.py test channel

  # Test some utility functions
  ./manage.py test docutil


You should see these lines at the end:

::

  Ran x tests in xs

  OK

If you use MySQL, you may see some error messages at the end of the unit tests:
as long as the OK is printed, you should ignore these annoying error messages.

If you see these lines instead, there was an error and you should contact me:

::

  Ran x tests in xs

  FAILED (failures=x, skipped=x)  


User Guide
----------

TBD

Creating a project
~~~~~~~~~~~~~~~~~~

TBD


Analyzing a codebase
~~~~~~~~~~~~~~~~~~~~

TBD


Analyzing documentation
~~~~~~~~~~~~~~~~~~~~~~~

TBD


Analyzing support channels
~~~~~~~~~~~~~~~~~~~~~~~~~~

TBD

Analyzing code snippets
~~~~~~~~~~~~~~~~~~~~~~~

TBD

Linking models
~~~~~~~~~~~~~~

TBD


Recommendations
~~~~~~~~~~~~~~~

TBD


License
-------

This software is licensed under the `New BSD License`. See the `LICENSE` file
in the for the full license text.

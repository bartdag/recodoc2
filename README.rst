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


**Documentation Analysis**

crawling
  Given a URL, downloads all the documentation pages of an HTML document.

parsing
  Parses a document and creates a model: sections, pages, code-like terms,
  code snippets.


**Support Channel Analysis**

crawling
  Given a URL to a forum or a mailing list archive, downloads all the messages.

parsing
  Parses a support channel archive and creates a model: support threads,
  messages, code-like terms, code snippets.


**Code-like Terms and Snippets Analysis**

snippet classification
  Classifies code snippets into the following categories: Java code snippet,
  Java exception stack trace, XML snippet, log trace.

snippet parsing
  Compiles Java code snippets to resolve and infer missing types. Parses
  snippets (Java and XML) to extra a list of code-like terms.

code-like terms classification
  Classifies code-like terms into likely code element kind. For example, the
  word ``FooBar`` is classified as a ``class``.


**Model Linking**

Java model linking
  Links Java codebases with Java code-like terms found in documentation and support
  channels.

XML model linking
  Links XML model with xml code-like terms found in documentation and support
  channels. *The code is not ported yet to this new version.*
  

**Documentation Improvements Recommendation**

This is currently being implemented.


Requirements
------------

This is a list of libraries and programs that need to be installed and
configured prior to install Recodoc. All of the other dependencies are covered
in the Installation section.


General Requirements
~~~~~~~~~~~~~~~~~~~~

* Python 2.7 (Python 2.6 or 3.0+ will not work).


Requirements for Code Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These libraries and programs are required to analyze Java codebases. Code
Analysis is also a prerequisite for Java snippet parsing, model linking,
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
* PostgreSQL
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
  source .virtualenvs/recodoc2/bin/activate


Step 2. Install the required dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  
  pip install django
  pip install lxml
  pip install pyenchant
  pip install Py4J
  pip install chardet


Step 3. Install the optional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, install the following Python libraries

::

  # This is for postgresql databases
  pip install psycopg2

  # This is for memcached
  pip install pylibmc

  # This is for the advanced Python shell
  pip install ipython

Then, install Py4J in Eclipse using the following update site:
``http://py4j.sourceforge.net/py4j_eclipse``.

Finally, install PPA in Eclipse using the following update site:
``http://www.sable.mcgill.ca/ppa/site_1.2.x``.

Since PPA is updated frequently but not released regularly, you might be better
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


License
-------

This software is licensed under the `New BSD License`. See the `LICENSE` file
in the for the full license text.

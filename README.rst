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
Java codebases is a prerequisite for Java snippet parsing, model linking, and
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
  
  pip install django==1.3.1
  pip install lxml==2.3.4
  pip install pyenchant==1.6.5
  pip install Py4J==0.7
  pip install chardet==1.0.1
  pip install django-devserver==0.3.1
  pip install pylibmc==1.2.0
  pip install ipython==0.10

  # For PostgreSQL (requires gcc. otherwise download the binary)
  pip install psycopg2==2.4.1

If you want to install pyscopg2 without compiling it (e.g., on windows),
download the `binary package <http://www.initd.org/psycopg/download/>`_.


Step 3. Install the optional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These dependencies are only required if you want to analyze Java code. First,
install Py4J in Eclipse using the following update site:
``http://py4j.sourceforge.net/py4j_eclipse``.

Then, install PPA in Eclipse using the following update site:
``http://www.sable.mcgill.ca/ppa/site_1.2.x``.

Since PPA is updated frequently but not released often, it might be better
to download it and build the update site locally. The source code is
`located on bitbucket <https://bitbucket.org/barthe/ppa/wiki/Home>`_.  

Step 4. Install the development dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to contribute to Recodoc, install the following Python programs:

::

  pip install gitli
  pip install coverage
  pip install django-test-coverage


Step 5. Download and Install Recodoc
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, clone the Recodoc git repository.

::

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

This short user guide will show you how to analyze the codebases,
documentation, and support channels of a project.

The guide assumes that you are located in the ``recodoc2`` directory containing
the manage.py script and that this script has the executable permission.

A list of all the available commands are available by issuing the help command:

::

  ./manage.py help

  # Print info about a specific command and its options:

  ./manage.py help createproject


Currently, it takes many small commands to analyze the artifacts of a project:
this is done on purpose to ease troubleshooting. It is easier to help you if I
know that an error occurred in a smaller command than if it occurred in a big
command that does everything. Moreover, some of the operations can be lengthy,
so it makes sense to break them in smaller steps.

This guide will assume that you want to analyze the `HttpClient
<http://hc.apache.org/httpcomponents-client-ga/index.html>`_ project. Steps for
other projects should be easy to infer.


Navigating the model
~~~~~~~~~~~~~~~~~~~~

The various models generated by Recodoc can be seen, searched, and edited
through a web interface. Just run the following command to start a webserver:

::

  ./manage.py runserver

Then open your web browser to ``http://localhost:8000/admin`` and enter the
username and password to you provided when you executed the ``syncdb``
command.


Initializing Recodoc
~~~~~~~~~~~~~~~~~~~~

The following step will create a bunch of metadata in the database. It should
complete quickly and without error: this is thus a good first step!

This command should only be issued once after running the ``syncdb`` command.

::

  ./manage.py initcodekind


Creating a project
~~~~~~~~~~~~~~~~~~

Create a project by issuing the following command. 

::

  ./manage.py createproject --pname hclient --pfullname 'HttpClient Library' --url 'http://hc.apache.org/httpcomponents-client-ga/index.html' --local

Note that a project will be created in the database and a folder will be
created in the Recodoc data directory specified in the PROJECT_FS_ROOT
variable in the localsettings.py file. Commands that begin by "create" usually
create a model in the database. They can optionnally initialize the required
directory structure if the ``--local`` flag is provided. Alternatively, there
is always the possibility to invoke the "createXlocal" command. The rationale
is that sometimes, it can be useful to transfer the local data, but not the
database from one machine to another.

If you want to analyze the code and the documentation of a project, you need to
create ``project releases``:

::

  ./manage.py createrelease --pname hclient --release '4.0' --is_major
  ./manage.py createrelease --pname hclient --release '4.1'


Analyzing a codebase
~~~~~~~~~~~~~~~~~~~~

To analyze a codebase, you will need to have Eclipse installed with Py4J. You
can open Eclipse yourself or use this command:

::

  ./manage.py starteclipse


Execute this command to create a codebase model and the appropriate directory
structure:

::

  ./manage.py createcode --pname hclient --bname main --release '4.0' --local

Then, execute the following command to add the project to the Eclipse
workspace. You will see that a project name htclientmain4.0 is created. It
contains a src folder for the source code and a lib folder for the libraries
(e.g., jar files). Once the project is added to Eclipse, add the source code
and the dependencies to this project.

*Note that the project is only "linked" in the Eclipse workspace. The actual
source code and structure resides in the PROJECT_FS_ROOT/code directory*.

::

  ./manage.py linkeclipse --pname hclient --bname main --release '4.0'


Once the project compiles under Eclipse, execute the following command to
generate the codebase model. Recodoc will go through the code in the project
and generate the appropriate code elements in the database (e.g., packages,
classes, methods, fields, hierarchy relationships).

::

  ./manage.py parsecode --pname htclient --bname main --release '4.0' --parser java
  

If there is any problem while parsing the code (e.g., you notice a compilation
error that you missed first or you want to add some packages), you can execute
this command to delete the model (just rerun the parsecode command after):

::

  ./manage.py clearcode --pname htclient --bname main --release '4.0' --parser java

Finally, if you want to see the difference between two codebase releases, you
can use the Recodoc codediff command:

::
  
  ./manage.py codediff --pname htclient --bname main --release1 4.0 --release2 4.1

The codebase diff report is available through the web interface (under
Codediffs).


Analyzing documentation
~~~~~~~~~~~~~~~~~~~~~~~

Execute the following command to create the appropriate model and directory
structure:

::

    ./manage.py createdoc --pname htclient --release 4.0 --dname clienttut \
    --parser doc.parser.common_parsers.NewDocBookParser \
    --url "file:///local_path/httpcomponents-client-4.0.1/tutorial/html/index.html" \
    --local

The ``url`` parameter can be a local or remote (e.g., http) path. The
documentation will be downloaded starting from this URL.

The ``parser`` parameter refers to the Python class responsible for generating
a model from the documents. There is also an optional ``syncer`` parameter if
the documentation is not contained in a subdirectory (e.g., a wiki has a flat
structure when it comes to URL so if you use the default "syncer", all pages
in the wiki will be included, not just the ones that are related to the
developer documentation.





Analyzing support channels
~~~~~~~~~~~~~~~~~~~~~~~~~~

To analyze a support channel, you will need to perform the following steps:

#. Get a table of contents of all the threads or messages.
#. Get the url of all threads and messages.
#. Download all pages containing each thread or messages.
#. Parse each page to generate a model of threads and messages and identify the
   code snippets and the code-like terms.


First, create a channel using the following command:

::
  
  ./manage.py createchannel --pname hclient --cfull_name usermail --cname usermail \
  --syncer channel.syncer.common_syncers.ApacheMailSyncer \
  --parser channel.parser.common_parsers.ApacheMailParser \
  --url 'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/' --local


Note that the ``syncer`` and ``parser`` parameters refer to the Python class
responsible for crawling the channel (syncer) and generating a model from it
(parser).

After you have created the channel structure, you need to retrieve the table
of contents. This should not take long.

::

  ./manage.py tocrefresh --pname hclient --cname usermail
  ./manage.py tocview --pname hclient --cname usermail

The next step is to download the sections in the table of contents. A section
is a page listing messages or threads. For example, for a mailing list, a
section is a page for a month (e.g., the page showing all messages for
December 2010). For a forum, a section is a page in the forum index (Page 1
for threads 0 to 40, Page 2 for threads 41 to 80, etc.).

::
  
  # This will download sections in increment of 20. This is recommended. 
  ./manage.py tocdownload --pname hclient --cname usermail --start 0 --end 20
  ./manage.py tocdownload --pname hclient --cname usermail --start 20 --end 40
  ./manage.py tocdownload --pname hclient --cname usermail --start 40 --end -1
  ./manage.py tocview --pname hclient --cname usermail

  # You can also download all sections in one go:
  ./manage.py tocdownload --pname hclient --cname usermail --start 0 --end -1
  ./manage.py tocview --pname hclient --cname usermail

You can now download the individual messages or threads. Each message/thread
is identified by an index. Indexes are incremented by 1000 for each table of
contents sections. For example, the first (hypothetical) 50 messages in
December 2010 are indexed from 0 to 49. The first 25 messages in January 2011
are indexed from 1000 to 1024 and so on.

::

  ./manage.py tocviewentries --pname hclient --cname usermail
  ./manage.py tocdownloadentries --pname hclient --cname usermail --start 0 --end 1000
  ./manage.py tocdownloadentries --pname hclient --cname usermail --start 1000 --end 2000
  ./manage.py tocviewentries --pname hclient --cname usermail
  # Continue until -1

You can see that the pages are downloaded in the
``PROJECT_FS_ROOT/hclient/channel/usermail`` directory.

Finally, if you want to parse these messages and generate a model
(channel/support threads/messages/code-like terms/code snippets), you can
execute this command:

::

  ./manage.py parsechannel --pname hclient --cname usermail

If it ever happens that an error occurred while parsing or that you find a bug
in your parser, you can delete the generated model from the db with this
command:

::

  ./manage.py clearchannel --pname hclient --cname usermail


Analyzing code snippets
~~~~~~~~~~~~~~~~~~~~~~~

Once you have analyzed the documentation and the support channel, you need to
further analyze the code snippets identified by Recodoc. In the following
step, individual code-like terms will be extracted from the code snippets.

This step assumes that Eclipse is running. Run the command once to parse all
snippets from the documentation, then from the support channel.

::

  ./manage.py parsesnippets --pname hclient --parser java --source d
  ./manage.py parsesnippets --pname hclient --parser java --source s


If there is a problem while parsing the code snippets (e.g., there is a
thunderstorm and your computer crashes), you can delete all the code-like
terms that were extracted from the code snippets with this command:

::

  ./manage.py clearsnippets --pname hclient --language j --source d


Linking models
~~~~~~~~~~~~~~

Once all code-like terms have been identified and classified, you can ask
Recodoc to link the terms with specific code elements. Run these two commands
to start the linking process:

::
  
  # Link code elements from main 4.0 with terms in documentation from 4.0
  ./manage.py linkall --pname hclient --bname main --release 4.0  --srelease 4.0 --source d

  # Link code elements from main 4.0 with terms in the support channel
  ./manage.py linkall --pname hclient --bname main --release 4.0  --source s

Note that it is possible to link different releases together: for example, you
could try to link the release 4.1 of the codebase with the release 4.0 of the
documentation.

Linking large support channels can take several days on modern hardware so it
makes sense to divide the work in smaller chunks. Contact me if you want to
learn how to do this.

If you want to remove all links and start again (e.g., because you found a bug
in the linker...), execute these commands:

::

  # To clear all the links.
  ./manage.py clearlinks --pname hclient --release 4.0 --source d
  ./manage.py clearlinks --pname hclient --release 4.0 --source s

  # Restore the original classification computed by the parser
  ./manage.py restorekinds --pname hclient --release 4.0 --source d
  ./manage.py restorekinds --pname hclient --release 4.0 --source s


Recommendations
~~~~~~~~~~~~~~~

Here we will generate recommendations for version 4.1 by analyzing the documents of both versions 4.0 and 4.1 of the client tutorial.

::

  # To clear all the links.
  ./manage.py clearlinks --pname hclient --release 4.0 --source d
  
  # Link for version 4.0 to 4.0
  ./manage.py linkall --pname hclient --bname main --release 4.0  --srelease 4.0 --source d
  # Link for version 4.1 to 4.1
  ./manage.py linkall --pname hclient --bname main --release 4.1  --srelease 4.1 --source d
  # Link against previous version
  ./manage.py linkall --pname hclient --bname main --release 4.1  --srelease 4.0 --source d
  
  # Computes link differences
  ./manage.py doclinkdiff --pname hclient --bname main --release1 4.0  --release2 4.1
  
  # Compute and compare coverage
  ./manage.py computefamilies --pname hclient --bname main --release 4.0
  ./manage.py computefamilies --pname hclient --bname main --release 4.1
  ./manage.py computedoccoverage --pname hclient --bname main --release 4.0 --dname clienttut --srelease 4.0
  ./manage.py computedoccoverage --pname hclient --bname main --release 4.1 --dname clienttut --srelease 4.0
  ./manage.py comparecoverage --pname hclient --bname main --release1 4.0 --release2 4.1 --source d --pk 1
  
  # Compute and show addition recommendations
  ./manage.py computeaddrecs --pname hclient --bname main --release1 4.0 --release2 4.1 --source d --pk 1
  ./manage.py showaddrecs --pname hclient --bname main --release1 4.0 --release2 4.1 --source d --pk 1
  
  # Compute and show deletion recommendations
  ./manage.py computeremoverecs --pname hclient --bname main --release1 4.0 --release2 4.1 --source d --pk 1
  ./manage.py showremoverecs --pname hclient --bname main --release1 4.0 --release2 4.1 --source d --pk 1

List of Implemented Parsers and Syncers
---------------------------------------

For now, please look in the following modules:

* doc.syncer.generic_syncer (SingleURLSyncer)
* doc.syncer.common_syncers
* doc.parser.common_parsers
* doc.parser.special_parsers
* channel.syncer.common_syncers
* chanel.parser.common_parsers


License
-------

This software is licensed under the `New BSD License`. See the `LICENSE` file
in the for the full license text.


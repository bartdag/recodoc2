from __future__ import unicode_literals
from django.conf import settings
from django.db import connection
import os
import shutil

def clean_test_dir():
    basepath = settings.PROJECT_FS_ROOT_TEST
    
    for member in os.listdir(basepath):
        full_path = os.path.join(basepath,member)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

"""Debugging queries in django for Django."""
def coroutine(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start

@coroutine
def QueryPrinter():
    """Initialize a query printer coroutine.
    
    Example use:
    >>> query_printer = QueryPrinter()
    >>> offset = len(conntection.queries)
    >>> # do some stuff that creates SQL queries
    >>> query_printer.send(offset)
    
    Now it would print the queries if this example had some. Example Output
    looks like:
    
    2 QUERIES AT OFFSET 556
    Time/s | SQL
    00.006 | 'SELECT ...'
    00.006 | 'INSERT INTO ...'
    """
    connection.queries = []
    settings.DEBUG = True
    offset = 0
    
    while True:
        diff = len(connection.queries) - offset
        
        if diff:
            print diff, "QUERIES AT OFFSET", offset
            print "Time/s | SQL"
            
            for query in connection.queries[offset:]:
                print "%06.3f | '%s'" % (float(query['time']), query['sql'])
        offset = (yield)

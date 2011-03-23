from __future__ import unicode_literals
import os
import time
from django.db import transaction


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

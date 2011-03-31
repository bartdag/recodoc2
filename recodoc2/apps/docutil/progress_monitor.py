from __future__ import unicode_literals
from threading import RLock


class NullProgressMonitor(object):
    def info(self, info):
        pass

    def start(self, task='', work=100):
        pass

    def work(self, info='', amount=1):
        pass

    def done(self):
        pass


class CLIProgressMonitor(object):
    def __init__(self, min_step=-1):
        self.min_step = min_step
        self.last_current = 0.0

    def info(self, info):
        print('Progress info: {0}'.format(info))

    def start(self, task='', work=100.0):
        print('Started task "{0}" - 0%'.format(task))
        self.total_work = float(work)
        self.current_work = 0.0
        self.task = task
        self.last_current = 0.0

    def work(self, info='', amount=1.0):
        self.current_work += amount
        progress = float(self.current_work) * 100.0 / self.total_work
        if self.min_step == -1 or (
                (progress - self.last_current) >= self.min_step):
            print('{0} - {1:.2f}%'.format(info, progress))
            self.last_current = progress

    def done(self):
        print('Done "{0}" - 100%'.format(self.task))


class CLILockProgressMonitor(object):
    '''Thread-safe Progress Monitor. Useful to share among multiple worker
       threads.'''

    def __init__(self):
        self.lock = RLock()

    def info(self, info):
        print('Progress info: {0}'.format(info))

    def start(self, task='', work=100.0):
        print('Started task "{0}" - 0%'.format(task))
        self.total_work = float(work)
        self.current_work = 0.0
        self.task = task

    def work(self, info='', amount=1.0):
        with self.lock:
            self.current_work += amount
        print('{0} - {1:.2f}%'.format(info, float(self.current_work) *
            100.0 / self.total_work))

    def done(self):
        print('Done "{0}" - 100%'.format(self.task))

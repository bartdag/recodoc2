from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from codebase.actions import stop_eclipse

class Command(NoArgsCommand):
    help = "Stop Eclipse"
    
    def handle_noargs(self, **options):
        stop_eclipse()

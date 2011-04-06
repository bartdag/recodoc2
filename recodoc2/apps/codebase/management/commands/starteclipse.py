from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from codebase.actions import start_eclipse

class Command(NoArgsCommand):
    help = "Start Eclipse"
    
    def handle_noargs(self, **options):
        start_eclipse()

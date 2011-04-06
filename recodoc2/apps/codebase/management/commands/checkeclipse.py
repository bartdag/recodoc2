from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from codebase.actions import check_eclipse

class Command(NoArgsCommand):
    help = "Check Eclipse"
    
    def handle_noargs(self, **options):
        check_eclipse()

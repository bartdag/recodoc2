from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from codebase.actions import create_code_element_kinds

class Command(NoArgsCommand):
    help = "Init Code Element Kinds"
    
    def handle_noargs(self, **options):
        create_code_element_kinds()

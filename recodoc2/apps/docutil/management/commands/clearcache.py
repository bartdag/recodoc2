from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from docutil.cache_util import clear_cache

class Command(NoArgsCommand):
    help = "Clear cache"
    
    def handle_noargs(self, **options):
        clear_cache()


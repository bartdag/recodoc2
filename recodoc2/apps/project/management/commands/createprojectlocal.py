from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from optparse import make_option
from project.actions import create_project_local
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name to initialize'),
    )
    help = "Initialize local directory structure"

    def handle_noargs(self, **options):
        create_project_local(smart_decode(options.get('pname')))

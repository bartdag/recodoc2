from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from optparse import make_option
from project.actions import create_project_db, create_project_local
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='default', help='Project unix name to initialize'),
        make_option('--pfullname', action='store', dest='pfullname',
            default='Default Project', help='Project name'),
        make_option('--url', action='store', dest='url',
            default='http://example.com', help='Project URL'),
        make_option('--local', action='store_true', dest='local',
            default=False, help='Set to create local directory'),
    )
    help = "Initialize local directory structure"

    @recocommand
    def handle_noargs(self, **options):
        create_project_db(smart_decode(options.get('pfullname')),
                          smart_decode(options.get('url')),
                          smart_decode(options.get('pname')))
        if (options.get('local', False)):
            create_project_local(smart_decode(options.get('pname')))

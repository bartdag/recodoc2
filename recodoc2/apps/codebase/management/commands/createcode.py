from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import create_code_local, create_code_db, link_eclipse


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--link', action='store_true', dest='link',
            default=False, help='Link to Eclipse Workspace'),
        make_option('--local', action='store_true', dest='local',
            default=False, help='Set to create local codebase'),

    )
    help = "Create a codebase"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        create_code_db(pname, bname, release)
        if options.get('local', False):
            create_code_local(pname, bname, release)
            if options.get('link', False):
                link_eclipse(pname, bname, release)

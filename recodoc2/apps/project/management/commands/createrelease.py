from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from optparse import make_option
from project.actions import create_release_db
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Release Number'),
        make_option('--is_major', action='store_true', dest='link',
            default=False, help='Is it a major version'),

    )
    help = "Create a project version"

    @recocommand
    def handle_noargs(self, **options):
        create_release_db(smart_decode(options.get('pname')),
                          smart_decode(options.get('release')),
                          smart_decode(options.get('link', False)))

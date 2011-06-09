from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import link_code


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--linker', action='store', dest='linker',
            default='-1', help='Linker used to link code elements'),
        make_option('--source', action='store', dest='source',
            default='-1', help='Source of code references'),
        make_option('--srelease', action='store', dest='srelease',
            default='-1', help='Release of the code references '
            '(optional for channels'),

    )
    help = "Link code"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        linker = smart_decode(options.get('linker'))
        source = smart_decode(options.get('source'))
        srelease = smart_decode(options.get('srelease'))
        link_code(pname, bname, release, linker, source, srelease)

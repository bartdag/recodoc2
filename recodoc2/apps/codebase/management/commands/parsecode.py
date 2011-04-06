from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import parse_code


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--parser', action='store_true', dest='link',
            default='-1', help='Parser used to create the code elements '
            '(optional)'),
        make_option('--input', action='store', dest='input',
            default='-1', help='Parser\'s input'),

    )
    help = "Parse a codebase"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        parser = smart_decode(options.get('parser'))
        pinput = smart_decode(options.get('input'))
        parse_code(pname, bname, release, parser, pinput)

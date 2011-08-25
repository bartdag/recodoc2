from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from doc.actions import remove_page
from optparse import make_option
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--dname', action='store', dest='dname',
            default='-1', help='Document name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--regex', action='store', dest='regex',
            default='-1', help='Regex pattern matched against the page url'),
    )
    help = "Remove pages from a document"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        dname = smart_decode(options.get('dname'))
        release = smart_decode(options.get('release'))
        regex = smart_decode(options.get('regex'))
        remove_page(pname, dname, release, regex)

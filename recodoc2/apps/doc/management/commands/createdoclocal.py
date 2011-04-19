from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand
from docs.actions import create_doc_local
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
        make_option('--syncer', action='store', dest='syncer',
            default='doc.syncer.generic_syncer.SingleURLSyncer',
            help='Syncer Python name'),
        make_option('--url', action='store', dest='url',
            default='-1', help='Channel URL'),

    )
    help = "Initialize documentation local model"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        dname = smart_decode(options.get('dname'))
        release = smart_decode(options.get('release'))
        url = smart_decode(options.get('url'))
        syncer = smart_decode(options.get('syncer'))
        create_doc_local(pname, dname, release, syncer, url)

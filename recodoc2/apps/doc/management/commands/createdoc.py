from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand
from doc.actions import create_doc_db, create_doc_local
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
        make_option('--parser', action='store', dest='parser',
            default='-1', help='Parser Python name'),
        make_option('--url', action='store', dest='url',
            default='-1', help='Document URL'),
        make_option('--local', action='store_true', dest='local',
            default=False, help='Set to create local document'),

    )
    help = "Initialize documentation model"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        dname = smart_decode(options.get('dname'))
        release = smart_decode(options.get('release'))
        url = smart_decode(options.get('url'))
        syncer = smart_decode(options.get('syncer'))
        parser = smart_decode(options.get('parser'))
        create_doc_db(pname, dname, release, url, syncer, parser)
        if (options.get('local', False)):
            create_doc_local(pname, dname, release, syncer, url)

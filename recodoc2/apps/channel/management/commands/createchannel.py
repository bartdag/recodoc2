from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand
from channel.actions import create_channel_db, create_channel_local
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cfull_name', action='store', dest='cfull_name',
            default='-1', help='Channel full name'),
        make_option('--cname', action='store', dest='cname',
            default='-1', help='Channel name'),
        make_option('--syncer', action='store', dest='syncer',
            default='channel.syncer.common_syncers.ApacheMailSyncer',
            help='Syncer Python name'),
        make_option('--parser', action='store', dest='parser',
            default='-1', help='Parser Python name'),
        make_option('--url', action='store', dest='url',
            default='-1', help='Channel URL'),
        make_option('--local', action='store_true', dest='local',
            default=False, help='Set to create local channel'),

    )
    help = "Initialize channel model"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        cfull_name = smart_decode(options.get('cfull_name'))
        url = smart_decode(options.get('url'))
        syncer = smart_decode(options.get('syncer'))
        parser = smart_decode(options.get('parser'))
        create_channel_db(pname, cfull_name, cname, syncer, parser, url)
        if (options.get('local', False)):
            create_channel_local(pname, cname, syncer, url)


from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand
from channel.actions import create_channel_local
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cname', action='store', dest='cname',
            default='-1', help='Channel name'),
        make_option('--syncer', action='store', dest='syncer',
            default='channel.syncer.common_syncers.ApacheMailSyncer',
            help='Syncer Python name'),
        make_option('--url', action='store', dest='url',
            default='-1', help='Channel URL'),

    )
    help = "Initialize local channel model"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        url = smart_decode(options.get('url'))
        syncer = smart_decode(options.get('syncer'))
        create_channel_local(pname, cname, syncer, url)



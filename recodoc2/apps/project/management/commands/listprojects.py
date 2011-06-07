from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from optparse import make_option
from project.actions import list_projects_local, list_projects_db


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--local', action='store_true', dest='local',
            default=False, help='List local projects only'),
    )
    help = "Initialize local directory structure"

    def handle_noargs(self, **options):
        header = ''
        projects = []
        if options.get('local', False):
            header = 'Local projects:'
            projects = list_projects_local()
        else:
            header = 'Projects in DB:'
            projects = list_projects_db()

        print(header)
        for project in projects:
            print('  ' + project)

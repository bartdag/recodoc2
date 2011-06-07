from __future__ import unicode_literals
from django.contrib import admin
from project.models import Project, ProjectRelease, Person


class PersonAdmin(admin.ModelAdmin):
    list_display = ('pk', 'nickname')
    search_fields = ('pk', 'nickname')


class ProjectReleaseInline(admin.StackedInline):
    model = ProjectRelease
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    fields = ['name', 'dir_name', 'url']
    inlines = [ProjectReleaseInline]


admin.site.register(Project, ProjectAdmin)
admin.site.register(Person, PersonAdmin)

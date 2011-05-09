from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.contenttypes import generic
from codebase.models import SingleCodeReference, CodeSnippet
from channel.models import SupportChannel, SupportThread, Message


class SingleCodeReferenceInline(generic.GenericTabularInline):
    fields = ('content', 'kind_hint', 'declaration',
            'snippet', 'project')
    raw_id_fields = ('snippet',)
    model = SingleCodeReference
    ct_field = 'local_content_type'
    ct_fk_field = 'local_object_id'
    extra = 0


class CodeSnippetInline(generic.GenericTabularInline):
    fields = ('language', 'project', 'snippet_text')
    model = CodeSnippet
    ct_field = 'local_content_type'
    ct_fk_field = 'local_object_id'
    extra = 0
    ordering = ('index',)


class MessageAdmin(admin.ModelAdmin):
    ordering = ('title',)
    list_filter = ('sthread__channel',)
    list_display = ('pk', 'sthread', 'title')
    list_display_links = ('title',)
    search_fields = ['title', 'id']
    inlines = [SingleCodeReferenceInline, CodeSnippetInline]


class MessageInline(admin.StackedInline):
    model = Message
    extra = 0
    ordering = ('title',)


class SThreadAdmin(admin.ModelAdmin):
    inlines = [MessageInline]
    ordering = ('title',)
    list_display = ('pk', 'channel', 'title')
    list_filter = ('channel',)
    list_display_links = ('title',)
    search_fields = ['title']


class SThreadInline(admin.StackedInline):
    model = SupportThread
    extra = 0
    ordering = ('title',)


class ChannelAdmin(admin.ModelAdmin):
    inlines = [SThreadInline]


admin.site.register(SupportChannel, ChannelAdmin)
admin.site.register(SupportThread, SThreadAdmin)
admin.site.register(Message, MessageAdmin)

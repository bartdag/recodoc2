from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.contenttypes import generic
from codebase.models import SingleCodeReference, CodeSnippet
from doc.models import Document, Page, Section, DocDiff, SectionChanger


class SingleCodeReferenceInline(generic.GenericTabularInline):
    fields = ('content', 'kind_hint', 'declaration',
            'snippet', 'first_link', 'project')
    readonly_fields = ('first_link',)
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


class SectionAdmin(admin.ModelAdmin):
    ordering = ('title',)
    list_filter = ('page__document', 'page')
    list_display = ('pk', 'page', 'title')
    list_display_links = ('title',)
    search_fields = ['title', 'id']
    inlines = [SingleCodeReferenceInline, CodeSnippetInline]


class SectionInline(admin.StackedInline):
    model = Section
    extra = 0
    ordering = ('title',)


class PageAdmin(admin.ModelAdmin):
    inlines = [SectionInline]
    ordering = ('title',)
    list_display = ('document', 'title')
    list_filter = ('document',)
    list_display_links = ('title',)
    search_fields = ['title']


class PageInline(admin.StackedInline):
    model = Page
    extra = 0
    ordering = ('title',)


class DocumentAdmin(admin.ModelAdmin):
    inlines = [PageInline]


class SectionChangerInline(admin.StackedInline):
    model = SectionChanger
    fields = ('section_from', 'section_to', 'words_from', 'words_to',
            'change')
    readonly_fields = ('section_from', 'section_to')
    extra = 0
    ordering = ('section_from',)


class DocDiffAdmin(admin.ModelAdmin):
    readonly_fields = ('removed_pages', 'added_pages', 'removed_sections',
            'added_sections')
    inlines = [SectionChangerInline]


admin.site.register(Document, DocumentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(DocDiff, DocDiffAdmin)

from __future__ import unicode_literals
from django.contrib import admin
from doc.models import Document, Page, Section


class PageInline(admin.StackedInline):
    model = Page
    extra = 0
    ordering = ('title',)


class DocumentAdmin(admin.ModelAdmin):
    inlines = [PageInline]


admin.site.register(Document, DocumentAdmin)


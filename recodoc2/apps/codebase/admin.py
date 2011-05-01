from __future__ import unicode_literals
from codebase.models import CodeBase, CodeElementKind, CodeElement,\
        SingleCodeReference, CodeSnippet, CodeElementFilter, ParameterElement
from django.contrib import admin


class AttributeCodeElementAdmin(admin.TabularInline):
    model = ParameterElement
    fk_name = 'attcontainer'
    fields = ('type_fqn', 'simple_name', 'index')
    extra = 0


class CodeElementAdmin(admin.ModelAdmin):
    fields = ('simple_name', 'fqn', 'kind', 'parser', 'attcontainer',
            'type_attcontainers', 'containers', 'type_containers', 'parents')
    list_filter = ('codebase', 'kind', 'parser')
    list_display = ('pk', 'fqn', 'simple_name', 'kind', 'parser')
    list_display_links = ('fqn', 'simple_name')
    search_fields = ['id', 'simple_name', 'fqn']
    filter_horizontal = ['containers', 'parents']
    raw_id_fields = ('attcontainer', 'containers', 'parents',
            'type_containers', 'type_attcontainers')
    inlines = [AttributeCodeElementAdmin]


class SingleCodeReferenceAdmin(admin.ModelAdmin):
    fields = ('content', 'kind_hint', 'sentence', 'paragraph', 'snippet',
            'xpath', 'url', 'source', 'local_object_id', 'mid_object_id',
            'global_object_id')
    list_display = ('content', 'kind_hint', 'source')
    list_display_links = ('content',)
#    readonly_fields = ('potential_elements', 'code_element')
    list_filter = ('source', 'kind_hint', )
    search_fields = ['id', 'content']
    #raw_id_fields = ('code_element', 'potential_elements')
#    filter_horizontal = ['potential_elements']


class SingleCodeReferenceInline(admin.TabularInline):
    model = SingleCodeReference
    fk_name = 'snippet'
    fields = ('content', 'source')
    extra = 0


class CodeSnippetAdmin(admin.ModelAdmin):
    list_display = ('pk', 'language', 'source', 'local_object_id',
            'global_object_id',)
    list_filter = ('source', 'language', )
    search_fields = ['id', 'local_object_id', 'global_object_id', ]
    inlines = [SingleCodeReferenceInline]


class CodeElementFilterAdmin(admin.ModelAdmin):
    list_filter = ('codebase', )
    search_fields = ('fqn', )


admin.site.register(CodeBase)
admin.site.register(CodeElementFilter, CodeElementFilterAdmin)
admin.site.register(CodeElementKind)
admin.site.register(CodeElement, CodeElementAdmin)
admin.site.register(SingleCodeReference, SingleCodeReferenceAdmin)
admin.site.register(CodeSnippet, CodeSnippetAdmin)

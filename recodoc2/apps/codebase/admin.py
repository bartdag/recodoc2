from __future__ import unicode_literals
from codebase.models import CodeBase, CodeElementKind, CodeElement,\
        SingleCodeReference, CodeSnippet, CodeElementFilter,\
        ParameterElement, CodeBaseDiff, CodeElementLink
from django.contrib import admin


class AttributeCodeElementAdmin(admin.TabularInline):
    model = ParameterElement
    fk_name = 'attcontainer'
    fields = ('type_fqn', 'simple_name', 'index')
    extra = 0


class CodeElementAdmin(admin.ModelAdmin):
    fields = ('simple_name', 'fqn', 'kind', 'deprecated', 'parser',
            'attcontainer', 'type_attcontainers', 'containers', 
            'type_containers', 'parents')
    list_filter = ('codebase', 'kind', 'parser', 'deprecated')
    list_display = ('pk', 'fqn', 'simple_name', 'kind', 'parser')
    list_display_links = ('fqn', 'simple_name')
    search_fields = ['id', 'simple_name', 'fqn']
    filter_horizontal = ['containers', 'parents']
    raw_id_fields = ('attcontainer', 'containers', 'parents',
            'type_containers', 'type_attcontainers')
    inlines = [AttributeCodeElementAdmin]


class CodeElementLinkInline(admin.TabularInline):
    model = CodeElementLink
    fields = ('code_element', 'index', 'rationale', 'linker_name')
    readonly_fields = ('code_element',)
    extra = 0


class SingleCodeReferenceAdmin(admin.ModelAdmin):
    fields = ('content', 'kind_hint', 'sentence', 'paragraph', 'snippet',
            'xpath', 'url', 'source', 'local_object_id', 'mid_object_id',
            'global_object_id', 'original_kind_hint')
    list_display = ('content', 'kind_hint', 'source')
    list_display_links = ('content',)
#    readonly_fields = ('potential_elements', 'code_element')
    list_filter = ('source', 'kind_hint', )
    search_fields = ['id', 'content']
    inlines = [CodeElementLinkInline]
    #raw_id_fields = ('code_element', 'potential_elements')
#    filter_horizontal = ['potential_elements']


class SingleCodeReferenceInline(admin.TabularInline):
    model = SingleCodeReference
    fk_name = 'snippet'
    fields = ('content', 'source', 'first_link')
    readonly_fields = ('first_link',)
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


class CodeBaseDiffAdmin(admin.ModelAdmin):
    fields = ('codebase_from', 'codebase_to', 'packages_size_from',
            'packages_size_to', 'types_size_from', 'types_size_to',
            'methods_size_from', 'methods_size_to', 'dep_types_size_from',
            'dep_types_size_to',
            'dep_methods_size_from', 'dep_methods_size_to', 'fields_size_from',
            'fields_size_to', 'enum_values_size_from', 'enum_values_size_to',
            'ann_fields_size_from', 'ann_fields_size_to', 'added_packages',
            'removed_packages', 'added_types', 'removed_types',
            'added_deprecated_types', 'removed_deprecated_types',
            'added_deprecated_methods', 'removed_deprecated_methods')
    readonly_fields = ('added_packages', 'removed_packages', 'added_types',
        'removed_types', 'added_deprecated_types', 'removed_deprecated_types',
        'added_deprecated_methods', 'removed_deprecated_methods')


class CodeElementLinkAdmin(admin.ModelAdmin):
    fields = ('code_reference', 'code_element', 'index', 'rationale',
        'linker_name')
    readonly_fields = ('code_reference', 'code_element')
    search_fields = ('id', )
    list_filter = ('release_link_set__project_release',
            'code_reference__project_release', 'code_element__kind', 'index',
            'code_reference__source')




admin.site.register(CodeBase)
admin.site.register(CodeElementFilter, CodeElementFilterAdmin)
admin.site.register(CodeElementKind)
admin.site.register(CodeElement, CodeElementAdmin)
admin.site.register(SingleCodeReference, SingleCodeReferenceAdmin)
admin.site.register(CodeSnippet, CodeSnippetAdmin)
admin.site.register(CodeBaseDiff, CodeBaseDiffAdmin)
admin.site.register(CodeElementLink, CodeElementLinkAdmin)

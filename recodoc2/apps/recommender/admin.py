from __future__ import unicode_literals
import recommender.models as rmodel
from django.contrib import admin


class CodePatternCoverageInline(admin.TabularInline):
    model = rmodel.CodePatternCoverage
    fk_name = 'pattern'
    fields = ('coverage', )
    extra = 0


class CodePatternAdmin(admin.ModelAdmin):
    fields = ('head', 'criterion1', 'criterion2', 'token', 'token_pos',
        'codebase', 'extension')
    readonly_fields = ('head', 'extension')
    search_fields = ('token',)
    list_filter = ('codebase', 'criterion1', 'criterion2', 'token_pos', 'kind')
    list_display = ('pk', 'head', 'token', 'criterion1', 'criterion2')
    inlines = [CodePatternCoverageInline]


class CodePatternCoverageAdmin(admin.ModelAdmin):
    fields = ('pattern', 'coverage', 'source')
    readonly_fields = ('pattern',)
    search_fields = ('pattern__pk', 'pattern__token')
    list_display = ('pattern', 'coverage', 'source')
    list_filter = ('source', 'pattern__codebase', 'pattern__criterion1',
        'pattern__criterion2', 'pattern__kind', 'valid')

class DocumentationPatternAdmin(admin.ModelAdmin):
    list_display = ('main_pattern', )
    list_filter = ('main_pattern__pattern__criterion1',
    'main_pattern__pattern__criterion2', 'main_pattern__pattern__kind')


#class CoverageDiffAdmin(admin.ModelAdmin):
    #readonly_fields = ('coverage_from', 'coverage_to')
    #list_display = ('coverage_from', 'coverage_diff', 'extension_diff')


#class FamilyDiffAdmin(admin.ModelAdmin):
    #readonly_fields = ('family_from', 'family_to')
    #list_display = ('family_from', 'coverage_diff', )


#class AddRecommendationAdmin(admin.ModelAdmin):
    #readonly_fields = ('coverage_diff', 'new_members', 'super_rec',
        #'old_members')


#class SuperAddRecommendationAdmin(admin.ModelAdmin):
    #readonly_fields = ('initial_rec', 'best_rec')


admin.site.register(rmodel.CodePattern, CodePatternAdmin)
admin.site.register(rmodel.CodePatternCoverage, CodePatternCoverageAdmin)
admin.site.register(rmodel.DocumentationPattern, DocumentationPatternAdmin)
#admin.site.register(rmodel.CoverageDiff, CoverageDiffAdmin)
#admin.site.register(rmodel.FamilyDiff, FamilyDiffAdmin)
#admin.site.register(rmodel.AddRecommendation, AddRecommendationAdmin)
#admin.site.register(rmodel.SuperAddRecommendation, SuperAddRecommendationAdmin)

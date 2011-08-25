from __future__ import unicode_literals
import recommender.models as rmodel
from django.contrib import admin


class FamilyCoverageInline(admin.TabularInline):
    model = rmodel.FamilyCoverage
    fk_name = 'family'
    fields = ('coverage', )
    extra = 0


class CodeElementFamilyAdmin(admin.ModelAdmin):
    fields = ('head', 'criterion1', 'criterion2', 'token', 'token_pos',
        'codebase', 'members')
    readonly_fields = ('head', 'members')
    search_fields = ('token',)
    list_filter = ('codebase', 'criterion1', 'criterion2', 'token_pos', 'kind')
    list_display = ('pk', 'head', 'token', 'criterion1', 'criterion2')
    inlines = [FamilyCoverageInline]


class FamilyCoverageAdmin(admin.ModelAdmin):
    fields = ('family', 'coverage', 'source')
    readonly_fields = ('family',)
    search_fields = ('family__pk', 'family__token')
    list_display = ('family', 'coverage', 'source')
    list_filter = ('source', 'family__codebase', 'family__criterion1',
        'family__criterion2', 'family__kind')


class CoverageDiffAdmin(admin.ModelAdmin):
    readonly_fields = ('coverage_from', 'coverage_to')
    list_display = ('coverage_from', 'coverage_diff', 'members_diff')


class FamilyDiffAdmin(admin.ModelAdmin):
    readonly_fields = ('family_from', 'family_to')
    list_display = ('family_from', 'members_diff', )


class AddRecommendationAdmin(admin.ModelAdmin):
    readonly_fields = ('coverage_diff', 'new_members', 'super_rec',
        'old_members')


class SuperAddRecommendationAdmin(admin.ModelAdmin):
    readonly_fields = ('initial_rec', 'best_rec')


admin.site.register(rmodel.CodeElementFamily, CodeElementFamilyAdmin)
admin.site.register(rmodel.FamilyCoverage, FamilyCoverageAdmin)
admin.site.register(rmodel.CoverageDiff, CoverageDiffAdmin)
admin.site.register(rmodel.FamilyDiff, FamilyDiffAdmin)
admin.site.register(rmodel.AddRecommendation, AddRecommendationAdmin)
admin.site.register(rmodel.SuperAddRecommendation, SuperAddRecommendationAdmin)

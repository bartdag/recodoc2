from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from codebase.models import SOURCE_TYPE, CodeBase, CodeElement,\
    CodeElementKind

PREFIX = 'p'

SUFFIX = 's'

MIDDLE = 'm'

DECLARATION = 'd'

HIERARCHY = 'h'

HIERARCHY_D = 'hd'

UNUSED = 'u'

TOKEN = 't'

NO_ABSTRACT = 'na'

TOKEN_POS = (
    (PREFIX, 'Prefix'),
    (SUFFIX, 'Suffix'),
    (MIDDLE, 'Middle'),
)

PATTERN_INTENSION = (
    # First criteria
    (DECLARATION, 'Declaration'),
    (HIERARCHY, 'Hierarchy'),
    (HIERARCHY_D, 'Hierarchy Descendants'),
    (NO_ABSTRACT, 'No Abstract'),
    # Second criteria
    (TOKEN, 'Token'),
    (UNUSED, 'Unused')
)


COVERAGE_THRESHOLD = 0.40


class CodePattern(models.Model):
    '''A code pattern contains all related code element based on a
       criteria (declaration, hierarchy, token).'''

    head = models.ForeignKey(CodeElement, blank=True, null=True,
            related_name='families')
    '''att.'''

    codebase = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='families')
    '''att.'''

    criterion1 = models.CharField(max_length=2, choices=PATTERN_INTENSION,
            blank=True, null=True)
    '''att.'''

    criterion2 = models.CharField(max_length=2, choices=PATTERN_INTENSION,
            blank=True, null=True, default=UNUSED)
    '''att.'''

    token = models.CharField(max_length=250, blank=True, null=True)
    '''att.'''

    token_pos = models.CharField(max_length=1, choices=TOKEN_POS,
            default=MIDDLE)
    '''att.'''

    kind = models.ForeignKey(CodeElementKind, blank=True, null=True)
    '''att.'''

    extension = models.ManyToManyField(CodeElement, blank=True, null=True,
            related_name='patterns')
    '''att.'''

    def equiv(self, pattern):
        equiv = True
        if self.head is None:
            equiv = pattern.head is None
        elif pattern.head is None:
            equiv = False
        else:
            equiv = self.head.human_string() == pattern.head.human_string()

        equiv = equiv and (self.kind == pattern.kind)
        equiv = equiv and (self.criterion1 == pattern.criterion1)
        equiv = equiv and (self.criterion2 == pattern.criterion2)
        equiv = equiv and (self.token == pattern.token)
        equiv = equiv and (self.token_pos == pattern.token_pos)

        return equiv

    def get_coverage(self, source, resource_pk):
        coverage_info = None

        for temp in self.coverage_infos.all():
            if temp.resource_object_id == resource_pk and \
                    temp.source == source:
                coverage_info = temp
                break

        return coverage_info

    def __unicode__(self):
        return '({0}) - {1} - {2} {3} {4} {5} - {6} members'.format(
                self.pk,
                self.head,
                self.get_criterion1_display(),
                self.get_criterion2_display(),
                self.token,
                self.get_token_pos_display(),
                self.extension.count())

    class Meta:
        verbose_name = 'code pattern'

        verbose_name_plural = 'code patterns'


class CodePatternCoverage(models.Model):
    '''Coverage information for a code pattern'''

    pattern = models.ForeignKey(CodePattern, blank=True, null=True,
            related_name='coverage_infos')
    '''att.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_pattern_coverage')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Type of resource (doc or channel)'''

    coverage = models.FloatField(default=0.0)
    '''att.'''

    valid = models.BooleanField(default=True)
    '''att.'''

    def is_interesting(self):
        return self.pattern.extension.count() > 1 and \
                self.coverage >= COVERAGE_THRESHOLD

    def __unicode__(self):
        return '{0} - {1}'.format(self.pattern, self.coverage)

    class Meta:
        verbose_name = 'pattern coverage'

        verbose_name_plural = 'pattern coverages'


class CoverageDiff(models.Model):
    coverage_from = models.ForeignKey(CodePatternCoverage, blank=True,
            null=True, related_name='coverage_diffs_from')
    '''att.'''

    coverage_to = models.ForeignKey(CodePatternCoverage, blank=True, null=True,
            related_name='coverage_diffs_to')
    '''att.'''

    coverage_diff = models.FloatField(default=0)
    '''att.'''

    extension_diff = models.IntegerField(default=0)
    '''att.'''

    def compute_diffs(self):
        self.coverage_diff = \
                self.coverage_to.coverage - self.coverage_from.coverage
        self.extension_diff = \
                self.coverage_to.pattern.extension.count() -\
                self.coverage_from.pattern.extension.count()

    def __unicode__(self):
        return '{0} (init: {1}) : {2}'.format(self.coverage_diff,
                self.coverage_from.coverage, self.coverage_from.pattern)


class PatternDiff(models.Model):

    pattern_from = models.ForeignKey(CodePattern, blank=True, null=True,
            related_name='pattern_diffs_from')
    '''att.'''

    pattern_to = models.ForeignKey(CodePattern, blank=True, null=True,
            related_name='pattern_diffs_to')
    '''att.'''

    extension_diff = models.IntegerField(default=0)
    '''att.'''

    def compute_diffs(self):
        self.extension_diff = self.pattern.extension.count() -\
                self.pattern.extension.count()

    def __unicode__(self):
        return '{0} : {1}'.format(self.extension_diff, self.pattern_from)


class DocumentationPattern(models.Model):

    main_pattern = models.ForeignKey(CodePatternCoverage, blank=True,
            null=True, related_name='doc_pattern_mains')
    '''att.'''

    patterns = models.ManyToManyField(CodePatternCoverage, blank=True,
            null=True, related_name='doc_patterns')
    '''att.'''


class DocumentationPatternSingleLocation(models.Model):
    location_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='doc_pattern_locations')
    location_object_id = models.PositiveIntegerField(null=True, blank=True)
    location = generic.GenericForeignKey('location_content_type',
            'location_object_id')
    '''att.'''


class DocumentationPatternLocation(models.Model):

    doc_pattern = models.ForeignKey(DocumentationPattern, blank=True,
            null=True, related_name='doc_pattern_locations')
    '''att.'''

    single_section = models.BooleanField(default=False)
    '''att.'''

    single_page = models.BooleanField(default=False)
    '''att.'''

    multi_page = models.BooleanField(default=False)
    '''att.'''

    location = models.ForeignKey(DocumentationPatternSingleLocation,
            blank=True, null=True, related_name='doc_pattern_locations')
    '''att.'''

    locations = models.ManyToManyField(DocumentationPatternSingleLocation,
            blank=True, null=True, related_name='doc_pattern_multi_locations')
    '''att.'''

    coverage = models.FloatField(default=0.0)
    '''att.'''


#class HighLevelLink(models.Model):

    #msg_level = models.BooleanField(default=False)
    #'''att.'''

    #no_snippet = models.BooleanField(default=False)
    #'''att.'''

    #confidence_level = models.IntegerField(default=1)
    #'''att.'''

    #source_content_type = models.ForeignKey(ContentType, null=True,
            #blank=True, related_name='source_high_levels')
    #source_object_id = models.PositiveIntegerField(null=True, blank=True)
    #source = generic.GenericForeignKey('source_content_type',
            #'source_object_id')
    #'''Source is always a documentation artifact, unless the the src and dst
       #are the same.'''

    #dst_content_type = models.ForeignKey(ContentType, null=True,
            #blank=True, related_name='dst_high_levels')
    #dst_object_id = models.PositiveIntegerField(null=True, blank=True)
    #dst = generic.GenericForeignKey('dst_content_type',
            #'dst_object_id')
    #'''att.'''

    #common_code_elements = models.ManyToManyField(CodeElement, null=True,
            #blank=True, related_name='high_level_links')
    #'''att.'''


class AddRecommendation(models.Model):

    coverage_diff = models.ForeignKey(CoverageDiff, blank=True, null=True,
            related_name='add_recommendations')
    '''att.'''

    old_members = models.ManyToManyField(CodeElement, blank=True, null=True,
            related_name='add_recommendations_covered')
    '''att.'''

    new_members = models.ManyToManyField(CodeElement, blank=True, null=True,
            related_name='add_recommendations')
    '''att.'''

    super_rec = models.ForeignKey('SuperAddRecommendation', blank=True,
            null=True, related_name='recommendations')
    '''att.'''

    def __unicode__(self):
        return '{0} : {1}'.format(self.new_members.count(), self.coverage_diff)


class SuperAddRecommendation(models.Model):

    initial_rec = models.OneToOneField(AddRecommendation, blank=True,
            null=True, related_name='super_recommendation')
    '''att.'''

    best_rec = models.OneToOneField(AddRecommendation, blank=True, null=True,
            related_name='super_recommendation_best')
    '''att.'''

    index = models.IntegerField(default=-1)
    '''att.'''

    codebase_from = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='superaddrecos_from')
    '''att.'''

    codebase_to = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='superaddrecos_to')
    '''att.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_superaddrecos')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Type of resource (doc or channel)'''

    overloaded = models.BooleanField(default=False)
    '''If >50% of the recommendation is about overloaded methods.'''

    def __unicode__(self):
        if self.best_rec is None:
            return self.initial_rec.__unicode__()
        else:
            return self.best_rec.__unicode__()


class RemoveRecommendation(models.Model):

    code_element_from = models.ForeignKey(CodeElement, null=True,
            blank=True, related_name='remove_recommendation_froms')
    '''att.'''

    code_element_to = models.ForeignKey(CodeElement, null=True,
            blank=True, related_name='remove_recommendation_tos')
    '''att.'''

    deprecated_element = models.ForeignKey(CodeElement, null=True,
            blank=True, related_name='remove_recommendation_deprecateds')
    '''att.'''

    codebase_from = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='remove_recommendation_froms')
    '''att.'''

    codebase_to = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='remove_recommendation_tos')
    '''att.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_removerecs')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Type of resource (doc or channel)'''

    def human_string(self):
        return self.__unicode__()

    def __unicode__(self):
        if self.code_element_to is None:
            return '{0} was deleted in {1}'.\
                    format(self.code_element_from.human_string(),
                            self.codebase_to)
        elif self.deprecated_element is None:
            return 'Ref to {0} has probably changed in {1}'.\
                    format(self.code_element_from.human_string(),
                            self.codebase_to)
        else:
            return '{0} was deprecaded in {1}'.\
                    format(self.code_element_from.human_string(),
                            self.codebase_to)


class HighLink(object):
    def __init__(self, msg, section):
        self.msg = msg
        self.section = section
        self.codes = []


class CodeLink(object):
    def __init__(self, code_element):
        self.code_element = code_element
        self.pairs = []

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

FAMILY_CRITERIA = (
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
# Create your models here.
class CodeElementFamily(models.Model):
    '''A code element family contains all related code element based on a
       criteria (declaration, hierarchy, token).'''

    head = models.ForeignKey(CodeElement, blank=True, null=True,
            related_name='families')
    '''att.'''

    codebase = models.ForeignKey(CodeBase, blank=True, null=True,
            related_name='families')
    '''att.'''

    criterion1 = models.CharField(max_length=2, choices=FAMILY_CRITERIA,
            blank=True, null=True)
    '''att.'''

    criterion2 = models.CharField(max_length=2, choices=FAMILY_CRITERIA,
            blank=True, null=True, default=UNUSED)
    '''att.'''

    token = models.CharField(max_length=250, blank=True, null=True)
    '''att.'''

    token_pos = models.CharField(max_length=1, choices=TOKEN_POS,
            default=MIDDLE)
    '''att.'''

    kind = models.ForeignKey(CodeElementKind, blank=True, null=True)

    members = models.ManyToManyField(CodeElement, blank=True, null=True,
            related_name='families_members')
    '''att.'''

    def equiv(self, family):
        equiv = True
        if self.head is None:
            equiv = family.head is None
        elif family.head is None:
            equiv = False
        else:
            equiv = self.head.human_string() == family.head.human_string()

        equiv = equiv and (self.kind == family.kind)
        equiv = equiv and (self.criterion1 == family.criterion1)
        equiv = equiv and (self.criterion2 == family.criterion2)
        equiv = equiv and (self.token == family.token)
        equiv = equiv and (self.token_pos == family.token_pos)

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
                self.members.count())

    class Meta:
        verbose_name = 'family'

        verbose_name_plural = 'families'


class FamilyCoverage(models.Model):
    '''Coverage information for a code element family'''

    family = models.ForeignKey(CodeElementFamily, blank=True, null=True,
            related_name='coverage_infos')
    '''att.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_family_coverage')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Type of resource (doc or channel)'''

    coverage = models.FloatField(default=0.0)
    '''att.'''

    def is_interesting(self):
        return self.family.members.count() > 1 and \
                self.coverage >= COVERAGE_THRESHOLD

    def __unicode__(self):
        return '{0} - {1}'.format(self.family, self.coverage)

    class Meta:
        verbose_name = 'family coverage'

        verbose_name_plural = 'family coverages'


class CoverageDiff(models.Model):
    coverage_from = models.ForeignKey(FamilyCoverage, blank=True, null=True,
            related_name='coverage_diffs_from')
    '''att.'''

    coverage_to = models.ForeignKey(FamilyCoverage, blank=True, null=True,
            related_name='coverage_diffs_to')
    '''att.'''

    coverage_diff = models.FloatField(default=0)
    '''att.'''

    members_diff = models.IntegerField(default=0)
    '''att.'''

    def compute_diffs(self):
        self.coverage_diff = \
                self.coverage_to.coverage - self.coverage_from.coverage
        self.members_diff = \
                self.coverage_to.family.members.count() -\
                self.coverage_from.family.members.count()

    def __unicode__(self):
        return '{0} : {1}'.format(self.coverage_diff,
                self.coverage_from.family)


class FamilyDiff(models.Model):

    family_from = models.ForeignKey(CodeElementFamily, blank=True, null=True,
            related_name='family_diffs_from')
    '''att.'''

    family_to = models.ForeignKey(CodeElementFamily, blank=True, null=True,
            related_name='family_diffs_to')
    '''att.'''

    members_diff = models.IntegerField(default=0)
    '''att.'''

    def compute_diffs(self):
        self.members_diff = self.family_to.members.count() -\
                self.family_from.members.count()

    def __unicode__(self):
        return '{0} : {1}'.format(self.members_diff, self.family_from)


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

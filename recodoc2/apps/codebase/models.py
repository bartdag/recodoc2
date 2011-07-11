from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from project.models import Project, ProjectRelease, SourceElement


DOCUMENT_SOURCE = 'd'

CHANNEL_SOURCE = 's'


LANGUAGES = [
    ('j', 'Java'),
    ('p', 'Python'),
    ('pr', 'Properties'),
    ('x', 'XML'),
    ('jx', 'Java Stack Trace'),
    ('l', 'Log Trace'),
    ('r', 'Previous Message'),
    ('o', 'Other'),
]
'''Language of an element'''

SOURCE_TYPE = (
    (DOCUMENT_SOURCE, 'Document'),
    (CHANNEL_SOURCE, 'Support Channel'),
)


def add_language(lang_code, lang_name):
    global LANGUAGES
    found = False
    for (code, _) in LANGUAGES:
        if lang_code == code:
            found = True
            break
    if not found:
        LANGUAGES.append((lang_code, lang_name))


class CodeBase(models.Model):
    '''A codebase includes all the code of a project release'''

    name = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    project_release = models.ForeignKey(ProjectRelease)
    '''att.'''

    def __unicode__(self):
        return self.name + ' - ' + self.project_release.__unicode__()


class CodeElementKind(models.Model):
    '''A Code Element Kind determines the kind of code elements and
       references: e.g., a method, a field, an xml attribute.'''

    kind = models.CharField(max_length=255, null=True, blank=True, unique=True)
    '''att.'''

    is_type = models.BooleanField(default=False)
    '''True if the element can be considered a type (supports inheritance
       and has children).'''

    is_file = models.BooleanField(default=False)
    '''att.'''

    is_attribute = models.BooleanField(default=False)
    '''True if the element is part of a bigger element (attribute container)
       and can be assigned to a value.'''

    is_value = models.BooleanField(default=False)
    '''True if the element can be assigned to an attribute.'''

    def __unicode__(self):
        return self.kind


class CodeElementFilter(models.Model):
    '''A filter indicates to a linker that a certain class (or a member of
       that class) should not be linked because it does not belong to the
       codebase.'''

    codebase = models.ForeignKey(CodeBase, related_name='filters')
    '''att.'''

    fqn = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    include_snippet = models.BooleanField(default=True)
    '''If False, code references are not matched against this filter
       if they come from a code snippet.'''

    one_ref_only = models.BooleanField(default=False)
    '''If True, a code reference will be matched only if it is not
       attached to other references.'''

    include_member = models.BooleanField(default=False)
    '''If True, a code reference will not be matched if it refers to a member
       and it matches this filter. Otherwise, only the container of the
       reference is checked against the filter.'''

    def __unicode__(self):
        return self.fqn


class CodeElement(models.Model):
    '''A code element.'''

    codebase = models.ForeignKey(CodeBase, related_name='code_elements')
    '''att.'''

    simple_name = models.CharField(max_length=500, null=True, blank=True,
            db_index=True)
    '''Primarily used to match code references to code elements. Should not
       contain any reference to context, container, hierarchy, etc.'''

    fqn = models.CharField(max_length=500, null=True, blank=True,
            db_index=True)
    '''Fully Qualified Name. Should be unique'''

    kind = models.ForeignKey(CodeElementKind, null=True, blank=True)
    '''att.'''

    deprecated = models.BooleanField(default=False)
    '''att.'''

    abstract = models.BooleanField(default=False)
    '''att.'''

    eclipse_handle = models.CharField(max_length=500, null=True, blank=True)
    '''Handle that can be used to identify the code element in an Eclipse
       workspace.'''

    containers = models.ManyToManyField('self', related_name='containees',
            symmetrical=False)
    '''List of containers (e.g., when an element contains members)'''

    type_containers = models.ManyToManyField('self',
            related_name='type_containees', symmetrical=False)
    '''List of type containers (e.g., when an element contains another
       type).'''

    parents = models.ManyToManyField('self', related_name='children',
            symmetrical=False)
    '''List of parents (hierarchy)'''

    attcontainer = models.ForeignKey('self', related_name='attributes',
            null=True, blank=True)
    '''List of attribute containers (suppose that self is an attribute)'''

    type_attcontainers = models.ManyToManyField('self',
            related_name='type_attributes', null=True, blank=True,
            symmetrical=False)
    '''List of type attribute containers (suppose that self is a type
       attribute)'''

    index = models.PositiveIntegerField(default=0)
    '''att.'''

    parser = models.CharField(max_length=100, null=True, blank=True,
            default='-1')
    '''Parser that generated this code element (e.g., java, schema, dtd)'''

    def parameters(self):
        return ParameterElement.objects.filter(attcontainer=self).all()

    def human_string(self):
        human_string = self.fqn
        if self.kind is None:
            return human_string

        #if self.kind.kind == 'xml element':
            #human_string = '<%s>' % self.fqn
        #elif self.kind.kind == 'xml attribute' and \
            # self.attcontainer is not None:
            #human_string = '<%s %s="">' % (self.attcontainer.fqn, self.fqn)
        #elif self.kind.kind == 'xml attribute value':
            #attribute = self.containers.all()[0]
            #element = attribute.attcontainer
            #human_string = '<%s %s="%s">' % (element.fqn, attribute.fqn,
            # self.fqn)
        if self.kind.kind == 'method':
            #clazz = self.containers.all()[0].simple_name
            #count = self.attributes.count()
            human_string = self.fqn + '('
            for attribute in self.attributes.all():
                human_string += attribute.parameterelement.type_simple_name \
                        + ', '
            human_string += ')'
        #if self.kind.kind in \
                #{'field', 'enumeration value', 'annotation field'}:
            #human_string = self.fieldelement.type_simple_name
            #human_string += ' ' + self.fqn
        #elif self.kind.kind == 'method parameter':
            #method = self.attcontainer
            #clazz = method.containers.all()[0]
            #human_string = '%s.%s(%s="")' % (clazz.simple_name,
            # method.simple_name, self.simple_name)
        #return '{0} - ({1})'.format(human_string, self.pk)
        return human_string

    def __unicode__(self):
        return self.human_string()

    class Meta:
        ordering = ['index']


class FieldElement(CodeElement):
    '''A field/attribute/enumeration value/annotation method with a type'''

    type_simple_name = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    type_fqn = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''


class MethodElement(CodeElement):
    '''A method with parameters (considered attributes) and a return type.'''

    return_simple_name = models.CharField(max_length=500, null=True,
            blank=True)
    '''att.'''

    return_fqn = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    overloads = models.ManyToManyField('self')
    '''att.'''

    parameters_length = models.SmallIntegerField(null=True, blank=True,
            default=0)
    '''att.'''


class ParameterElement(CodeElement):
    '''A method parameter with a type and a position in the method parameters
       list. The method is the attcontainer.'''

    type_simple_name = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    type_fqn = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    def __unicode__(self):
        return str(self.index) + ':' + self.type_fqn

    class Meta:
        ordering = ['index']
        order_with_respect_to = 'attcontainer'


class MethodFamily(CodeElement):
    '''A collection of overloaded methods.'''

    methods = models.ManyToManyField(MethodElement, null=True, blank=True,
            related_name='method_family')
    '''Collection of overloaded methods. Should really be a foreign key of
       MethodElement, but it was added later and maybe we may want to create
       multiple families in the future (ah ah ah).'''

    references = models.ManyToManyField('SingleCodeReference', null=True,
            blank=True, related_name='method_family')
    '''att.'''


### CODE-LIKE TERMS ###

class CodeSnippet(SourceElement):
    '''A structured blurb of text representing a code snippets (e.g., Java
      statements, part of an XML configuration file, etc.)'''

    project = models.ForeignKey(Project, null=True, blank=True)
    '''Project the snippet belongs to'''

    project_release = models.ForeignKey(ProjectRelease, null=True, blank=True)
    '''Project Release the reference belongs to. Optional.'''

    language = models.CharField(max_length=2, null=True, blank=True,
            choices=LANGUAGES, default='j')
    '''Probable language of the snippet (e.g., java, xml)'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Where the snippet comes from (doc or support channel)'''

    snippet_text = models.TextField(null=True, blank=True)
    '''Content of the snippet'''

    index = models.IntegerField(null=True, blank=True, default=0)
    '''Used to identify a snippet in a container'''

    # E.g., section, message
    local_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='local_code_snippets')
    local_object_id = models.PositiveIntegerField(null=True, blank=True)
    local_context = generic.GenericForeignKey('local_content_type',
            'local_object_id')
    '''Most precise context, i.e., message or section that contains the
       snippet.'''

    # E.g., big section
    mid_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='mid_code_snippets')
    mid_object_id = models.PositiveIntegerField(null=True, blank=True)
    mid_context = generic.GenericForeignKey('mid_content_type',
            'mid_object_id')
    '''Medium context, i.e., a top-level section that contains the
       snippet.'''

    # E.g., big section
    global_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='global_code_snippets')
    global_object_id = models.PositiveIntegerField(null=True, blank=True)
    global_context = generic.GenericForeignKey('global_content_type',
            'global_object_id')
    '''Large context, i.e., thread or page that contains the snippet.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_code_snippets')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    def __unicode__(self):
        return "{0} - {1}".format(self.get_language_display(), self.pk)

    class Meta:
        ordering = ['index']


class SingleCodeReference(SourceElement):
    '''A reference to a single code element.'''

    project = models.ForeignKey(Project, null=True, blank=True)
    '''Project the reference belongs to'''

    project_release = models.ForeignKey(ProjectRelease, null=True, blank=True)
    '''Project Release the reference belongs to. Optional.'''

    content = models.TextField(null=True, blank=True)
    '''Textual content of the reference. Handle (custom format) if the code
       reference has been parsed from a snippet.'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Where the snippet comes from (doc or support channel)'''

    original_kind_hint = models.ForeignKey(CodeElementKind, null=True,
            blank=True, related_name='original_kinds')
    '''Original kind. Never changes!'''

    kind_hint = models.ForeignKey(CodeElementKind, null=True, blank=True)
    '''Probable kind of a reference (e.g., a Java method, an xml element)'''

    snippet = models.ForeignKey(CodeSnippet, null=True, blank=True,
            related_name='single_code_references')
    '''Snippet from which the code reference has been extracted. If null,
       then the reference was inlined in English content.'''

    declaration = models.BooleanField(default=False)
    '''Does the reference represents a declaration (e.g., class Foo is a
       declaration). Could be used to determine if a code reference belongs
       to an example or the real code base.'''

    index = models.IntegerField(null=True, blank=True, default=0)
    '''Used to identify a snippet in a container'''

    sentence = models.TextField(null=True, blank=True)
    '''Sentence (or line) in which the code reference was used.'''

    paragraph = models.TextField(null=True, blank=True)
    '''Paragraph in which the code reference was used.'''

    parent_reference = models.ForeignKey('self', null=True, blank=True,
            related_name='child_references')
    '''Reference from which this reference was extracted (e.g., when a
       reference may contain multiple code elements)'''

    child_index = models.IntegerField(null=True, blank=True, default=0)
    '''Reference order w.r.t. parent reference'''

    # E.g., title of section, message, thread...
    title_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='title_code_references')
    title_object_id = models.PositiveIntegerField(null=True, blank=True)
    title_context = generic.GenericForeignKey('title_content_type',
            'title_object_id')
    '''Reference in titles.'''

    # E.g., section, message
    local_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='local_code_references')
    local_object_id = models.PositiveIntegerField(null=True, blank=True)
    local_context = generic.GenericForeignKey('local_content_type',
            'local_object_id')
    '''Most precise context, i.e., message or section that contains the
       reference.'''

    # E.g., big section
    mid_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='mid_code_references')
    mid_object_id = models.PositiveIntegerField(null=True, blank=True)
    mid_context = generic.GenericForeignKey('mid_content_type',
            'mid_object_id')
    '''Medium context, i.e., a top-level section that contains the
       reference.'''

    # E.g., big section
    global_content_type = models.ForeignKey(ContentType, null=True, blank=True,
            related_name='global_code_references')
    global_object_id = models.PositiveIntegerField(null=True, blank=True)
    global_context = generic.GenericForeignKey('global_content_type',
            'global_object_id')
    '''Large context, i.e., thread or page that contains the reference.'''

    # E.g., a document or a channel
    resource_content_type = models.ForeignKey(ContentType, null=True,
            blank=True, related_name='resource_code_references')
    resource_object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = generic.GenericForeignKey('resource_content_type',
            'resource_object_id')
    '''A resource represents a specific document or channel.'''

    # Computed field!
    def first_link(self):
        try:
            link = CodeElementLink.objects.\
                    filter(code_reference=self).get(index=0)
            return link
        except Exception:
            return None

    def __unicode__(self):
        return '{0} - {1}'.format(self.content, str(self.pk))

    class Meta:
        ordering = ['index']


class CodeBaseDiff(models.Model):
    codebase_from = models.ForeignKey(CodeBase, null=True, blank=True,
            related_name='diffs_from')
    codebase_to = models.ForeignKey(CodeBase, null=True, blank=True,
            related_name='diffs_to')

    added_packages = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_p_added')
    removed_packages = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_p_removed')
    packages_size_from = models.IntegerField(default=0)
    packages_size_to = models.IntegerField(default=0)

    added_types = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_t_added')
    removed_types = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_t_removed')
    types_size_from = models.IntegerField(default=0)
    types_size_to = models.IntegerField(default=0)

    added_methods = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_m_added')
    removed_methods = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_m_removed')
    methods_size_from = models.IntegerField(default=0)
    methods_size_to = models.IntegerField(default=0)

    added_fields = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_f_added')
    removed_fields = models.ManyToManyField(CodeElement, null=True, blank=True,
            related_name='diffs_f_removed')
    fields_size_from = models.IntegerField(default=0)
    fields_size_to = models.IntegerField(default=0)

    added_enum_values = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_e_added')
    removed_enum_values = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_e_removed')
    enum_values_size_from = models.IntegerField(default=0)
    enum_values_size_to = models.IntegerField(default=0)

    added_ann_fields = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_a_added')
    removed_ann_fields = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_a_removed')
    ann_fields_size_from = models.IntegerField(default=0)
    ann_fields_size_to = models.IntegerField(default=0)

    added_deprecated_types = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_dep_t_added')
    removed_deprecated_types = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_dep_t_removed')
    dep_types_size_from = models.IntegerField(default=0)
    dep_types_size_to = models.IntegerField(default=0)

    added_deprecated_methods = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_dep_m_added')
    removed_deprecated_methods = models.ManyToManyField(CodeElement, null=True,
            blank=True, related_name='diffs_dep_m_removed')
    dep_methods_size_from = models.IntegerField(default=0)
    dep_methods_size_to = models.IntegerField(default=0)

    def __unicode__(self):
        return 'Diff {0} - {1}'.format(self.codebase_from, self.codebase_to)


### LINKS ###

class ReleaseLinkSet(models.Model):
    '''A set of potential links between a code reference and code elements
       from a project release.'''

    code_reference = models.ForeignKey(SingleCodeReference,
            related_name='release_links')
    '''att.'''

    project_release = models.ForeignKey(ProjectRelease,
            related_name='release_links')
    '''att.'''

    def __unicode__(self):
        return '{0} - {1}'.format(self.code_reference.content,
                self.project_release)


class Filter(models.Model):
    '''Linker filter used to filter and rank potential code elements.'''

    filter_name = models.CharField(max_length=250)
    '''att.'''

    executed = models.BooleanField(default=True)
    '''att.'''

    activated = models.BooleanField(default=True)
    '''att.'''

    size_before = models.IntegerField(default=0)
    '''Number of potential code elements before filtering.'''

    size_after = models.IntegerField(default=0)
    '''Number of potential code elements after filtering.'''

    index = models.IntegerField(default=0)
    '''Order of the filter'''

    release_link_set = models.ForeignKey(ReleaseLinkSet, blank=True, null=True)
    '''att.'''

    def __unicode__(self):
        return '{0} Executed: {1} Activated: {2} Before: {3} After: {4}'.\
                format(self.filter_name, self.executed, self.activated,
                       self.before, self.after)

    class Meta:
        ordering = ['index']


class CodeElementLink(models.Model):
    '''A link between a single code reference and a code element.'''

    code_reference = models.ForeignKey(SingleCodeReference,
            related_name='potential_links')
    '''att.'''

    code_element = models.ForeignKey(CodeElement,
            related_name='potential_links')
    '''att.'''

    index = models.IntegerField(default=0)
    '''0-based index. 0 = most probable link.'''

    rationale = models.CharField(max_length=250)
    '''Rationale of this link... often a filter name?'''

    linker_name = models.CharField(max_length=250)
    '''Linker that created this link.'''

    release_link_set = models.ForeignKey(ReleaseLinkSet, blank=True,
            null=True, related_name="links")
    '''att.'''

    first_link = models.OneToOneField(ReleaseLinkSet, blank=True, null=True,
            related_name='first_link')
    '''This attribute is only set when index=0. This is a shortcut to avoid
       searching based on index and to enable complex queries based on the
       first link.'''

    def __unicode__(self):
        return '{0} --> {1}'.format(self.code_reference.content,
                self.code_element.fqn)

    class Meta:
        ordering = ['index']


### Transient Classes ###

class MethodInfo(object):

    def __init__(self, method_name, fqn_container, nb_params, type_params):
        self.method_name = method_name
        self.fqn_container = fqn_container
        self.nb_params = nb_params
        self.type_params = type_params

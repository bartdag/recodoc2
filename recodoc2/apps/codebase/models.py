from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from project.models import Project, ProjectRelease, SourceElement


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
    ('d', 'Document'),
    ('s', 'Support Channel'),
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

    kind = models.CharField(max_length=500, null=True, blank=True, unique=True)
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

    parser = models.CharField(max_length=100, null=True, blank=True,
            default='-1')
    '''Parser that generated this code element (e.g., java, schema, dtd)'''

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
        #elif self.kind.kind == 'method parameter':
            #method = self.attcontainer
            #clazz = method.containers.all()[0]
            #human_string = '%s.%s(%s="")' % (clazz.simple_name,
            # method.simple_name, self.simple_name)
        return human_string

    def __unicode__(self):
        return self.human_string()


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

    index = models.PositiveIntegerField(default=0)
    '''att.'''

    def __unicode__(self):
        return str(self.index) + ':' + self.type_fqn

    class Meta:
        ordering = ['-index']


### CODE-LIKE TERMS ###

class CodeSnippet(SourceElement):
    '''A structured blurb of text representing a code snippets (e.g., Java
      statements, part of an XML configuration file, etc.)'''
    
    language = models.CharField(max_length=2, null=True, blank=True, 
            choices=LANGUAGES, default='j')
    '''Probable language of the snippet (e.g., java, xml)'''

#    detector_id = models.CharField(max_length=20, null=True, blank=True)
    project_releases = models.ManyToManyField(ProjectRelease)
    '''Code references may belong to many project releases depending on their
       source (support channel = many potential releases)'''

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
    global_content_type = models.ForeignKey(ContentType,null=True, blank=True,
            related_name='global_code_snippets')
    global_object_id = models.PositiveIntegerField(null=True, blank=True)
    global_context = generic.GenericForeignKey('global_content_type',
            'global_object_id')
    '''Large context, i.e., thread or page that contains the snippet.'''
    
    def __unicode__(self):
        return "%s - %i" % (self.get_language_display(), self.pk)
    
    class Meta:
        ordering = ['index']


class SingleCodeReference(SourceElement):
    '''A reference to a single code element.'''
    
    content = models.TextField(null=True, blank=True)
    '''Textual content of the reference. Handle (custom format) if the code
       reference has been parsed from a snippet.'''

    project_releases = models.ManyToManyField(ProjectRelease)
    '''Code references may belong to many project releases depending on their
       source (support channel = many potential releases)'''

    source = models.CharField(max_length=1, null=True, blank=True,
            choices=SOURCE_TYPE, default='d')
    '''Where the snippet comes from (doc or support channel)'''

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
    
    linker = models.CharField(max_length=100, null=True, blank=True,
            default="-1")
    '''Indicates which linker (e.g., java, java-generic) recovered the link
       between the code reference and the code element.'''
    
    sentence = models.TextField(null=True, blank=True)
    '''Sentence (or line) in which the code reference was used.'''
    
    paragraph = models.TextField(null=True, blank=True)
    '''Paragraph in which the code reference was used.'''
    
    parent_reference = models.ForeignKey('self',null=True,blank=True,
            related_name='child_references')
    '''Reference from which this reference was extracted (e.g., when a
       reference may contain multiple code elements)'''
    
    child_index = models.IntegerField(null=True,blank=True,default=0)
    '''Reference order w.r.t. parent reference'''
    
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
    global_content_type = models.ForeignKey(ContentType,null=True, blank=True,
            related_name='global_code_references')
    global_object_id = models.PositiveIntegerField(null=True, blank=True)
    global_context = generic.GenericForeignKey('global_content_type',
            'global_object_id')
    '''Large context, i.e., thread or page that contains the reference.'''
    
    def __unicode__(self):
        return '%s - %s' % (self.content, str(self.pk))
    
    class Meta:
        ordering = ['index']

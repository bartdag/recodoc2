from __future__ import unicode_literals
import re
import logging
from codeutil.parser import create_match
import docutil.str_util as su


logger = logging.getLogger("recodoc.codeutil.java")

### CONSTANTS ###

JAVA_LANGUAGE = 'j'

JAVA_EXCEPTION_TRACE = 'jx'

### FUNCTIONS ###


def clean_java_name(name):
    """Given a name, returns a tuple containing the simple name and the fully
    qualified name. Removes all array or generic artifacts.
    """
    # Replaces inner class artifact
    clean_name_fqn = name.replace('$', '.')

    # Clean Array
    index = clean_name_fqn.find('[')
    if index > -1:
        clean_name_fqn = clean_name_fqn[:index]

    # Clean Generic
    index = clean_name_fqn.find('<')
    if index > -1:
        clean_name_fqn = clean_name_fqn[:index]

    dot_index = clean_name_fqn.rfind('.')
    clean_name_simple = clean_name_fqn
    if dot_index > -1:
        clean_name_simple = clean_name_fqn[dot_index + 1:]

    return (clean_name_simple, clean_name_fqn)


### JAVA SNIPPET ###

JAVA_END_CHARACTERS = set([';', '{', '}'])
JAVA_START = ['@', '//', '/*', '*/', '**/']
THRESHOLD_JAVA = 0.20 

### JAVA EXCEPTION TRACE ###

THRESHOLD_EXCEPTION = 0.40


# Filters

class SQLFilter(object):

    def filter(self, lines, long_line):
        begin = False
        end = False
        for line in lines:
            begin = begin or line.strip().startswith('BEGIN')
            end = end or line.strip().startswith('END')
        return begin and end


class BuilderFilter(object):

    def filter(self, lines, long_line):
        builder_syntax = False

        for line in lines:
            if line.rstrip().endswith(';'):
                builder_syntax = False
                break
            elif line.find('={') > -1 and not line.startswith('@'):
                builder_syntax = True
        return builder_syntax


### REGEX METHODS ###

# Text Parsing
METHOD_SIGNATURE_TARGET_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])  # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)   # method name
    \([\s]*                               # opening parenthesis
    (?:(?P<first_argument_type>[a-zA-Z][\w\-_.<>]*)(?:[\W][a-zA-Z][\w\-_.]*))? # first argument 'Type name'
    (?:[\s]*,[\s]*([a-zA-Z][\w\-.<>]*[\s][a-zA-Z][\w\-.]*))*           # other arguments
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


METHOD_SIGNATURE_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])? # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (?:(?P<first_argument_type>[a-zA-Z][\w\-_.<>]*)(?:[\W][a-zA-Z][\w\-_.]*))? # first argument 'Type name'
    (?:[\s]*,[\s]*([a-zA-Z][\w\-.<>]*[\s][a-zA-Z][\w\-.]*))*           # other arguments
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


CALL_CHAIN_TARGET_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/]) # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*"                               # or string
    )
    )*
    [\s]*\)                               # closing parenthesis
    (?:
    \.                                    # call chain
    ([a-zA-Z][^(\s.]*)                    # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    )+
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


CALL_CHAIN_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])? # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    (?:
    \.                                    # call chain
    ([a-zA-Z][^(\s.]*)                    # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    )+                                    # One or more call
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


# Call chain?
SIMPLE_CALL_TARGET_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])  # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


SIMPLE_CALL_RE = re.compile(r'''
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])? # Target. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


SIMPLE_CALL_NO_TARGET_RE = re.compile(r'''
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


METHOD_DECLARATION_RE = re.compile(r'''
    ([^;=]*)                # anything is accepted before except java lines
    ([\w\-_<>]+)            # return type
    (\s+)                  # whitespaces
    (?P<method_name>[a-zA-Z][^(\s.]*)  # method name
    (\([^)]*\))            # parameters
    ([^{;]*)               # whitespaces, throws
    {                      # bracket
    ''', re.VERBOSE)


METHOD_DECLARATION_STRICT_RE = re.compile(r'''
    ([\s]*?)               # Only whitespaces accepted
    ([\w_\-<>]+)           # return type
    (\s+)                  # whitespaces
    (?P<method_name>[a-zA-Z][^(\s.]*)  # method name
    (\([^)]*\))            # parameters
    ([^{;]*)               # whitespaces, throws
    {                      # bracket
    ''', re.VERBOSE)


CONSTRUCTOR_CALL_RE = re.compile(r'''
    \bnew\s+                              # start constructor
    (?:(?P<target>[a-zA-Z][\w\-.<>]*)[.:#/])* # fqn. Does not begin with numbers or _ or -.
    (?P<method_name>[a-zA-Z][^(\s.]*)     # method name
    \([\s]*                               # opening parenthesis
    (                                     # first argument 'arg'
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )?
    (?:[\s]*,[\s]*
    (                                     # other arguments
    [\w\-_<>.]* |                         # non string arg
    "[^"]*" |                             # or string
    '[^']*'                               # or char
    )
    )*
    [\s]*\)                               # closing parenthesis
    [;]?                                  # optional ; at the end
    ''', re.VERBOSE)


### REGEX TYPES ###

FQN_RE = re.compile(r'''
    [a-zA-Z]           # Do not begin with numbers or _ or -
    [\w\-_]*           # any sequence of word char and dash
    (?:\.[\w_\-<>]+)+  # followed by a number of . + sequence of word char and dash
    ''', re.VERBOSE)


# Used if no FQN is found
SIMPLE_NAME_RE = re.compile(r'''
    [\w_\-]+
    ''', re.VERBOSE)


# This is the main camel case.
CAMEL_CASE_1_RE = re.compile(r'''
    [A-Za-z0-9]*            # Any word char except _
    [a-z][A-Z][a-z]         # aBa
    [A-Za-z0-9]*            # Any word char except _
    ''', re.VERBOSE)


# This is a special case.
CAMEL_CASE_2_RE = re.compile(r'''
    [A-Za-z0-9]*            # Any word char except _
    [A-Z][a-z][A-Z]         # BaB
    [A-Za-z0-9]*            # Any word char except _
    ''', re.VERBOSE)


# This is a special case + the main case
CAMEL_CASE_3_RE = re.compile(r'''
    [A-Za-z0-9]*            # Any word char except _
    [a-z][A-Z]              # aB (but not Ba)
    [A-Za-z0-9]+            # At least one word char except _ (so aBB is ok)
    ''', re.VERBOSE)


# This is a special case.
CAMEL_CASE_4_RE = re.compile(r'''
    [A-Za-z0-9]*            # Any word char except _
    [A-Z][A-Z]+[a-z]        # BAa
    [A-Za-z0-9]+            # Any word char except _
    ''', re.VERBOSE)


# This is to find all capitalize words. Identifies if there is a punctuation
# sign
TYPE_IN_MIDDLE_RE = re.compile(r'''
    (?P<dot>[.!?])?
    [\s"']+
    (?P<class>
    [A-Z]
    [\w_\-]+
    )
    \b
    ''', re.VERBOSE)


# Used only when we are not sure if this is an annotation or not...
ANNOTATION_PATTERN = re.compile('(?:@)?(?P<annotation>[^(]+)')

ANNOTATION_RE = re.compile(r'''
    @                           # Annotation mark
    (?P<annotation_name>        # Annotation name, possibly a FQN
    (?:[a-z][\w_\-]*\.)*
    [A-Z][\w_\-]*
    )
    ''', re.VERBOSE)


CLASS_DECLARATION_RE = re.compile(r'''
    ^
    \s*
    (public|protected|private|static|final)*
    \s*
    (class|interface|enum) # type of class
    (\s+)                  # whitespaces
    ([^{]+)                # name of class + generics + extends/implements
    {                      # bracket
    ''', re.VERBOSE)


ANONYMOUS_CLASS_DECLARATION_RE = re.compile(r'''
    ([^;{}()]*)            # anything is accepted except java lines
    \bnew\s                # new
    ([^;{}()]*)            # anything except java lines
    (\([^)]*\))            # parentheses
    [\s]*{
    ''', re.VERBOSE)


### REGEX FIELDS ###

CONSTANT_RE = re.compile(r'''
    [A-Z]               # Do not begin with numbers or _ or -
    [A-Z0-9]+           # Uppercase word
    (?:[_-][A-Z0-9]+)*  # Optionally separated by a _ and uppercase word
    ''', re.VERBOSE)


### REGEX EXCEPTION TRACES ###

EXCEPTION_PATTERN1 = re.compile(r'''Exception:''')
EXCEPTION_PATTERN2 = re.compile(r'''Caused by:''')
EXCEPTION_PATTERN3 = re.compile(r'''^[\s]*\bat\b (?:[\w\s]+)(?:\.[\s\w]+)*\(''') # at org.springframework.context.support.AbstractApplic ationContext.getBean(
EXCEPTION_PATTERN4 = re.compile(r'''^[\s]*at[\s]*$''') 
EXCEPTION_PATTERN5 = re.compile(r'''\.(?:java|class)\:(?:\d+)\)''') # .java:223)
EXCEPTION_PATTERN6 = re.compile(r'''\([\w\s]+\.(?:java|class)\:(?:\d+)''') # (Toto.java:223
EXCEPTION_LINE_PATTERN = re.compile(r'''[\s]*at[\s]*(?:[\w\s]+)(?:\.[\s\w]+)*\(.*\.(?:j\s*a\s*v\s*a\s*|\s*c\s*l\s*a\s*s\s*s\s*)\:(?:\d+)\)''')

EXCEPTION_PATTERNS = [EXCEPTION_PATTERN1, EXCEPTION_PATTERN2, 
                      EXCEPTION_PATTERN3, EXCEPTION_PATTERN4,
                      EXCEPTION_PATTERN5, EXCEPTION_PATTERN6]

### Java Body Recognition ###

def is_cu_body(text):
    new_text = su.clean_for_re(text)
    return CLASS_DECLARATION_RE.match(new_text) is not None


def is_class_body(text):
    new_text = su.clean_for_re(text)
    return ANONYMOUS_CLASS_DECLARATION_RE.match(new_text) is not None or\
           METHOD_DECLARATION_RE.match(new_text)


### Java Snippet Regognition ###

def is_java_snippet(text, filters=None):
    return is_java_lines(text.split('\n'), filters)


def get_clean_java_line(line):
    index = line.rfind('//')
    if index > -1:
        return line[:index].strip()

    index = line.rfind('/*')
    if index > -1:
        return line[:index].strip()

    return line.strip()


def is_java_lines(lines, filters=None):
    java_lines = 0
    empty_lines = 0
    for line in lines:
        clean_line = get_clean_java_line(line)
        clean_size = len(clean_line)
        if len(line.strip()) == 0:
            empty_lines += 1
        elif line.rstrip()[-1] in JAVA_END_CHARACTERS:
            java_lines += 1
        elif clean_size > 0 and clean_line[-1] in JAVA_END_CHARACTERS:
            java_lines += 1
        else:
            new_line = line.strip()
            for start in JAVA_START:
                if new_line.startswith(start):
                    java_lines += 1
                    break
    confidence = float(java_lines) / (len(lines) - empty_lines)

    is_java_kind = confidence >= THRESHOLD_JAVA

    if confidence > 0:
        logger.info('Java Lines: {0} {1} {2}'
            .format(java_lines, len(lines) - empty_lines, str(lines)))

    if is_java_kind and filters != None:
        long_text = su.join_text(lines, False)
        for filter in filters:
            if filter.filter(lines, long_text):
                is_java_kind = False
                logger.info('Not Java Kind. {0}'.format(long_text))
                break

    return (is_java_kind, confidence)


def is_exception_trace_lines(lines):
    exception_lines = 0
    for line in lines:
        for pattern in EXCEPTION_PATTERNS:
            if pattern.search(line):
                exception_lines += 1
                break
            
    lines_confidence = float(exception_lines) / len(lines)
    one_line_confidence = 0.0
    one_line = su.merge_lines(lines, False)
    if EXCEPTION_LINE_PATTERN.search(one_line):
        one_line_confidence = 1.0
        
    confidence = max(lines_confidence, one_line_confidence)
    
    if - 0.10 <= (confidence - THRESHOLD_EXCEPTION) <= 0:
        logger.info('Almost reached EXCEPTION threshold')
        logger.info(lines) 
    
    return (confidence >= THRESHOLD_EXCEPTION, confidence)



### Code Reference Identification and Classification ###

class ClassMethodStrategy(object):

    priority = 50

    def match(self, text):
        matches = set()
        for m in SIMPLE_CALL_TARGET_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'class', self.priority),
                        [(m.start(), m.end(), 'method', self.priority)]))
        for m in METHOD_SIGNATURE_TARGET_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'class', self.priority),
                        [(m.start(), m.end(), 'method', self.priority)]))
        for m in CALL_CHAIN_TARGET_RE.finditer(text):
            call_chain = text[m.start():m.end()]
            offset = m.start()
            children = []
            for child_match in SIMPLE_CALL_NO_TARGET_RE.finditer(call_chain):
                children.append(
                        (child_match.start() + offset,
                         child_match.end() + offset,
                         'method', self.priority))

            # Basically, the first child should still refer to the container
            first_child = [(m.start(), m.end(), 'method', self.priority)]
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'class', self.priority),
                        first_child + children[1:]))
        return matches


class MethodStrategy(object):

    priority = 25

    def match(self, text):
        matches = set()
        for m in SIMPLE_CALL_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'method', self.priority)))
        for m in METHOD_SIGNATURE_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'method', self.priority)))
        for m in CALL_CHAIN_RE.finditer(text):
            call_chain = text[m.start():m.end()]
            offset = m.start()
            children = []
            for child_match in SIMPLE_CALL_NO_TARGET_RE.finditer(call_chain):
                children.append(
                        (child_match.start() + offset,
                         child_match.end() + offset,
                         'method',
                         self.priority))

            # Basically, children[0] is == m except that the target
            # would not be there
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'method', self.priority),
                        children[1:]))
        for m in METHOD_DECLARATION_STRICT_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'method', self.priority)))
        return matches


class FieldStrategy(object):

    priority = 25

    def match(self, text):
        matches = set()
        for m in FQN_RE.finditer(text):
            (simple, _) = clean_java_name(m.group(0))
            if len(simple) > 0:
                if simple[0].islower() or CONSTANT_RE.match(simple):
                    matches.add(
                        create_match(
                            (m.start(), m.end(), 'class', self.priority),
                            [(m.start(), m.end(), 'field', self.priority)]))
        for m in CONSTANT_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'field', self.priority)))
        return matches


class OtherStrategy(object):

    priority = 15

    def match(self, text):
        matches = set()
        for m in FQN_RE.finditer(text):
            matches.add(
                    create_match((m.start(), m.end(), 'class', self.priority)))
        for m in CAMEL_CASE_1_RE.finditer(text):
            matches.add(
                    create_match((m.start(), m.end(), 'class', self.priority)))
        for m in CAMEL_CASE_2_RE.finditer(text):
            matches.add(
                    create_match((m.start(), m.end(), 'class', self.priority)))
        for m in CAMEL_CASE_3_RE.finditer(text):
            matches.add(
                    create_match((m.start(), m.end(), 'class', self.priority)))
        for m in CAMEL_CASE_4_RE.finditer(text):
            matches.add(
                    create_match((m.start(), m.end(), 'class', self.priority)))
        for m in TYPE_IN_MIDDLE_RE.finditer(text):
            if m.group('dot') is None:
                matches.add(create_match(
                    (m.start('class'), m.end('class'), 'class', self.priority))
                    )

        return matches


class AnnotationStrategy(object):

    priority = 25

    def match(self, text):
        matches = set()
        for m in ANNOTATION_RE.finditer(text):
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'annotation', self.priority)))
        return matches

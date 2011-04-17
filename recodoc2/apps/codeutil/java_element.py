from __future__ import unicode_literals
import re
import docutil.str_util as su



### METHODS ###

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
    (                                     # other arguments
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


### TYPES ###

FQN_RE = re.compile(r'''
    [a-zA-Z]           # Do not begin with numbers or _ or -
    [\w\-_]*           # any sequence of word char and dash
    (?:\.[\w_\-<>]+)+  # followed by a number of . + sequence of word char and dash
    ''', re.VERBOSE)


# Used if no FQN is found
SIMPLE_NAME_RE = re.compile(r'''
    [\w_\-]+
    ''',re.VERBOSE)


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
TYPE_IN_MIDDLE = re.compile(r'''
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


### FIELDS ###

CONSTANT_RE = re.compile(r'''
    [A-Z]               # Do not begin with numbers or _ or -
    [A-Z0-9]+           # Uppercase word
    (?:[_-][A-Z0-9]+)*  # Optionally separated by a _ and uppercase word
    ''', re.VERBOSE)


### Java Body Recognition ###

def is_cu_body(text):
    new_text = su.clean_for_re(text)
    return CLASS_DECLARATION_RE.match(new_text) is not None


def is_class_body(text):
    new_text = su.clean_for_re(text)
    return ANONYMOUS_CLASS_DECLARATION_RE.match(new_text) is not None or\
           METHOD_DECLARATION_RE.match(new_text)

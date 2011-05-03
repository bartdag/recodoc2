from __future__ import unicode_literals
import re
import unicodedata


MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
          'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

CAMELCASE_TOKEN = re.compile(r'((?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z]))')

STOPPERS = {'.', '!', '?', '\n', '\r'}

PAR_STOPPERS = {'\n', '\r'}

REPLY_LANGUAGE = 'r'
OTHER_LANGUAGE = 'o'
STOP_LANGUAGE = 's'

SPLIT_PATTERN = re.compile(r"[\w']+|[.,!?;]")


def get_original_title(title):
    original_title = title.replace('re:','').replace('RE:','').\
            replace('Re:','').replace('rE:','').strip()
    return original_title


def split_pos(text):
    '''Split some text and return a list of tuples of the form
       (word, start, end)'''
    splits = []
    for match in SPLIT_PATTERN.finditer(text):
        word = match.group(0)
        if word.isalnum():
            splits.append((word,match.start(),match.end()))
    return splits


def get_month_as_int(month_str):
    return MONTHS[month_str.lower()]


def smart_decode(s):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, str):
        # Should never reach this case in Python 3
        return unicode(s, 'utf-8')
    else:
        return unicode(s)


def tokenize(s):
    return CAMELCASE_TOKEN.sub(' ', s).split()


def normalize(uni_str):
    '''Ensures that a unicode string does not have strange characters.
       Necessary with lxml because it does not handle encoding well...'''
    if uni_str is None:
        return None
    elif not isinstance(uni_str, unicode):
        uni_str = smart_decode(uni_str)
    return unicodedata.normalize('NFKD', uni_str)


def find_list(original, to_find):
    '''Finds all ocurrences of a string and return a list of the positions.'''

    indexes = []
    index = 0
    size = len(original)
    while index < size:
        index = original.find(to_find, index)
        if (index > -1):
            indexes.append(index)
            index += 1
        else:
            break
    return indexes


def clean_for_re(original):
    return original.replace('\n', ' ')


def clean_breaks(original):
    return original.replace('\n', ' ').replace('\t', ' ').replace('\r', '')


def lower_stopper_index(paragraph, start, end, stoppers=STOPPERS):
    index = end
    for i, c in enumerate(reversed(paragraph[start:end])):
        if c in stoppers:
            index = end - i
    return index


def upper_stopper_index(paragraph, start, end, stoppers=STOPPERS):
    index = start
    for i, c in enumerate(paragraph[start: end]):
        if c in stoppers:
            index = start + i
    return index


def find_sentence(paragraph, start, end):
    paragraph_size = len(paragraph)
    first_stopper = upper_stopper_index(paragraph, 0, start)
    if first_stopper > 0:
        first_stopper += 1
    second_stopper = lower_stopper_index(paragraph, end, paragraph_size)
    return paragraph[first_stopper:second_stopper].strip()


def find_paragraph(paragraph, start, end):
    paragraph_size = len(paragraph)
    first_stopper = upper_stopper_index(paragraph, 0, start, PAR_STOPPERS)
    if first_stopper > 0:
        first_stopper += 1
    second_stopper = lower_stopper_index(paragraph, end, paragraph_size,
            PAR_STOPPERS)
    return paragraph[first_stopper:second_stopper].strip()


def join_text(lines, line_breaks=True):
    if line_breaks:
        text = '\n'.join(normalize(line).strip() for line in lines)
    else:
        text = ' '.join(clean_breaks(normalize(line)) for line in lines)
    return text


def get_paragraphs(lines, eat_extra_lines=0):
    paragraphs = []
    ate = 0
    content = False
    paragraph = []
    for line in lines:
        #print('DEBUG GETPARA %s' % line)
        if len(line.strip()) == 0:
            ate += 1
            if ate > eat_extra_lines:
                if content:
                    paragraphs.append(paragraph)
                content = False
                paragraph = []
                ate = 0
        else:
            paragraph.append(line)
            content = True
            ate = 0

    if content:
        paragraphs.append(paragraph)

    return paragraphs


def is_snippet(paragraph):
    return sum((1 for line in paragraph if line.strip() != '')) > 1


def get_paragraph_language(paragraph, p_classifiers):
    p_language = 'o'

    for (p_classifier, language) in p_classifiers:
        (ok, confidence) = p_classifier(paragraph)
        if ok:
            p_language = language
            break

    return p_language


def filter_paragraphs(paragraphs, p_classifiers):
    current_language = None
    current_snippet = []
    snippets = []
    new_paragraphs = []

    for paragraph in paragraphs:
        language = get_paragraph_language(paragraph, p_classifiers)
        #print('Language {0} Paragraph {1}'.format(language, paragraph))
        if language == STOP_LANGUAGE:
            break
        elif language != OTHER_LANGUAGE:
            if language == current_language:
                current_snippet.append('')
                current_snippet.extend(paragraph)
            else:
                if len(current_snippet) > 0:
                    if not is_snippet(current_snippet) or \
                        current_language == REPLY_LANGUAGE:
                        # we want to keep replies as snippet to better
                        # filter them later... if needed :-)
                        snippets.append((current_snippet, current_language))
                        current_snippet = []
                    else:
                        # Avoid single-line snippets
                        new_paragraphs.append(current_snippet)
                        current_snippet = []
                current_snippet.extend(paragraph)
                current_language = language
        else:
            new_paragraphs.append(paragraph)
            if len(current_snippet) > 0:
                snippets.append((current_snippet, current_language))
            current_language = None
            current_snippet = []

    if (len(current_snippet) > 0):
        snippets.append((current_snippet, current_language))

    return (new_paragraphs, snippets)


def merge_lines(lines, line_breaks=True):
    if line_breaks:
        text = '\n'.join(normalize(line).strip() for line in lines)
    else:
        text = ' '.join(clean_breaks(normalize(line)) for line in lines)
    return text

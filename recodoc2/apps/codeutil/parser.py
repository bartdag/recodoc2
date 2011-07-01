from __future__ import unicode_literals


def create_match(parent, children=None):
    if children is None:
        children = tuple()
    return (parent, tuple(children))


def is_valid_match(match, matches, filtered):
    '''Returns true if the match is new, bigger than an existing match,
       and not encapsulated by an existing match.'''
    valid = True
    ((start, end, kind, priority), _) = match
    for temp_match in matches:
        if temp_match in filtered or match == temp_match:
            continue
        ((temp_start, temp_end, temp_kind, temp_priority), _) = temp_match
        if start == temp_start and end == temp_end:
            if priority <= temp_priority:
                # More precise classification exists.
                valid = False
                break
        elif start >= temp_start and end <= temp_end:
            # Encapsulated in an existing match.
            valid = False
            break

    return valid


def find_parent_reference(current_kind, references, kinds_hierarchy):
    parent_kind = kinds_hierarchy[current_kind]
    for reference in reversed(references):
        if reference.kind_hint.kind == parent_kind:
            return reference

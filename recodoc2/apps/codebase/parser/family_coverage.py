from __future__ import unicode_literals
from collections import defaultdict
import codebase.models as cmodel
import codebase.linker.context as ctx
from docutil.progress_monitor import NullProgressMonitor, CLIProgressMonitor
from docutil.str_util import tokenize
from docutil.commands_util import size

# TODO
# 1- Work on token identification
# 2- Work on coverage


def create_family(head, criterion, first_criterion):
    family = cmodel.CodeElementFamily(head=head)
    if first_criterion:
        family.criterion1 = criterion
    else:
        family.criterion2 = criterion
    family.save()

    return family


def compute_declaration_family(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    families = {}

    progress_monitor.start('Comp. Declaration Families', size(code_elements))

    for code_element in code_elements:
        kind_pk = code_element.kind.pk
        for container in code_element.containers.all():
            pk = container.pk
            key = '{0}-{1}'.format(pk, kind_pk)
            if key not in families:
                families[key] = create_family(container, cmodel.DECLARATION,
                        first_criterion)
                families[key].kind = code_element.kind
                families[key].save()
            families[key].members.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return families


def compute_ancestors(code_element, ancestors):
    for parent in code_element.parents.all():
        if parent.pk not in ancestors:
            ancestors[parent.pk] = parent
            compute_ancestors(parent, ancestors)


def compute_hierarchy_family(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    families1 = {}
    familiesd = {}

    progress_monitor.start('Comp. Hierarchy Families', size(code_elements))

    for code_element in code_elements:
        # Hierarchy 1
        for parent in code_element.parents.all():
            pk = parent.pk
            if pk not in families1:
                families1[pk] = create_family(parent, cmodel.HIERARCHY,
                        first_criterion)
            families1[pk].members.add(code_element)

        # Hierarchy D
        ancestors_list = ctx.get_ancestors_value(code_element)
        ancestors = {ancestor.pk: ancestor for ancestor in ancestors_list}

        for ancestor_pk in ancestors:
            if ancestor_pk not in familiesd:
                familiesd[ancestor_pk] = create_family(
                        ancestors[ancestor_pk],
                        cmodel.HIERARCHY_D,
                        first_criterion)
            familiesd[ancestor_pk].members.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return (families1, familiesd)


def compute_token_family_second(families,
        progress_monitor=NullProgressMonitor()):

    progress_monitor.start('Computing token for a set of families',
            len(families))
    token_families = {}

    for head_pk in families:
        family = families[head_pk]
        code_elements = family.members.all()
        sub_families = compute_token_family(code_elements, False,
                CLIProgressMonitor())
        for key in sub_families:
            sub_family = sub_families[key]
            sub_family.head = family.head
            sub_family.criterion1 = family.criterion1
            sub_family.save()
            token_families[sub_family.pk] = sub_family
        progress_monitor.work('Family processed.', 1)

    progress_monitor.done()

    return token_families


def compute_tokens(code_elements):
    tokens = set()
    for code_element in code_elements.all():
        temp = [token.lower().strip() for token in
                tokenize(code_element.simple_name)]
        tokens.update(temp)
    return tokens


def compute_token_family(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    tokens = compute_tokens(code_elements)
    families = {}
    progress_monitor.start('Computing token for code elements', len(tokens))
    for token in tokens:
        start = defaultdict(list)
        end = defaultdict(list)
        middle = defaultdict(list)

        if first_criterion:
            addt = lambda d, e: d[e.kind.pk].append(e)
        else:
            addt = lambda d, e: d[0].append(e)

        for code_element in code_elements.all():
            name = code_element.simple_name.lower().strip()
            if name.startswith(token):
                addt(start, code_element)

            if name.endswith(token):
                addt(end, code_element)

            if name.find(token) > -1:
                addt(middle, code_element)

        for start_members in start.values():
            if len(start_members) > 1:
                family = create_family(None, cmodel.TOKEN, first_criterion)
                family.token = token
                family.token_pos = cmodel.PREFIX
                family.save()
                family.members.add(*start_members)
                families[family.pk] = family
                if first_criterion:
                    family.kind = start_members[0].kind
                    family.save()

        for end_members in end.values():
            if len(end_members) > 1:
                family = create_family(None, cmodel.TOKEN, first_criterion)
                family.token = token
                family.token_pos = cmodel.SUFFIX
                family.save()
                family.members.add(*end_members)
                families[family.pk] = family
                if first_criterion:
                    family.kind = end_members[0].kind
                    family.save()

        for mid_members in middle.values():
            if len(mid_members) > 1:
                family = create_family(None, cmodel.TOKEN, first_criterion)
                family.token = token
                family.token_pos = cmodel.MIDDLE
                family.save()
                family.members.add(*mid_members)
                families[family.pk] = family
                if first_criterion:
                    family.kind = mid_members[0].kind
                    family.save()

        progress_monitor.work('Processed a token')
    progress_monitor.done()
    return families


def compute_coverage(families, source, resource):
    for family in families:
        total = family.members.count()
        count = 0
        pk = resource.pk
        for member in family.members.all():
            if cmodel.CodeElementLink.objects.\
                    filter(code_element=member).\
                    filter(index=0).\
                    filter(code_reference__resource_object_id=pk).\
                    filter(code_reference__source=source).exists():
                count += 1
        if total > 0:
            coverage = float(count) / float(total)
        else:
            coverage = 0.0

        fam_coverage = cmodel.FamilyCoverage(family=family, resource=resource,
                source=source, coverage=coverage)
        fam_coverage.save()

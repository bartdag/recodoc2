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


def create_family(head, codebase, criterion, first_criterion):
    family = cmodel.CodeElementFamily(head=head)
    if first_criterion:
        family.criterion1 = criterion
    else:
        family.criterion2 = criterion
    family.codebase = codebase
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
                families[key] = create_family(container, container.codebase,
                        cmodel.DECLARATION, first_criterion)
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
                families1[pk] = create_family(parent, parent.codebase,
                        cmodel.HIERARCHY, first_criterion)
            families1[pk].members.add(code_element)

        # Hierarchy D
        ancestors_list = ctx.get_ancestors_value(code_element)
        ancestors = {ancestor.pk: ancestor for ancestor in ancestors_list}

        for ancestor_pk in ancestors:
            if ancestor_pk not in familiesd:
                familiesd[ancestor_pk] = create_family(
                        ancestors[ancestor_pk],
                        code_element.codebase,
                        cmodel.HIERARCHY_D,
                        first_criterion)
            familiesd[ancestor_pk].members.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return (families1, familiesd)


def compute_no_abstract_family(families,
        progress_monitor=NullProgressMonitor()):

    new_families = {}
    progress_monitor.start('Comp. No Abstract Families', size(families))

    for head_pk in families:
        family = families[head_pk]
        code_elements = family.members.all()
        new_members = [code_element for code_element in code_elements if
                code_element.abstract]
        size = len(new_members)
        if size > 0 and size < family.members.count():
            new_family = create_family(family.head, family.codebase,
                    cmodel.NO_ABSTRACT, False)
            new_family.criterion1 = family.criterion1
            new_family.save()
            new_families[new_family.pk] = new_family
        progress_monitor.work('Family processed', 1)

    progress_monitor.done()

    return new_families


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
    families = {}
    if size(code_elements) == 0:
        return families

    codebase = code_elements.all()[0].codebase
    tokens = compute_tokens(code_elements)
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
            element_tokens = tokenize(code_element.simple_name)

            if token not in element_tokens:
                continue
            elif name.startswith(token):
                addt(start, code_element)
            elif name.endswith(token):
                addt(end, code_element)
            elif name.find(token) > -1:
                addt(middle, code_element)

        for start_members in start.values():
            if len(start_members) > 1:
                family = create_family(None, codebase, cmodel.TOKEN,
                        first_criterion)
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
                family = create_family(None, codebase, cmodel.TOKEN,
                        first_criterion)
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
                family = create_family(None, codebase, cmodel.TOKEN,
                        first_criterion)
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


def compute_coverage(families, source, resource,
        progress_monitor=NullProgressMonitor):

    progress_monitor.start('Computing Coverage', size(families))

    for family in families.all():
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
        progress_monitor.work('Processed a family', 1)

    progress_monitor.done()


def compare_coverage(codebase_from, codebase_to, source, resource_pk,
        progress_monitor=NullProgressMonitor):

    (heads_from, tokens_from) = compute_family_index(codebase_from,
            progress_monitor)
    (heads_to, tokens_to) = compute_family_index(codebase_to, progress_monitor)

    removed = []
    added = []

    heads_family_diff = compute_family_diff(heads_from, heads_to, added,
            removed, progress_monitor)
    tokens_family_diff = compute_family_diff(tokens_from, tokens_to, added,
            removed, progress_monitor)

    progress_monitor.info('Sorting added/removed')
    removed.sort(key=lambda f: f.members.count(), reverse=True)
    added.sort(key=lambda f: f.members.count(), reverse=True)

    progress_monitor.info('Sorting family diff')
    heads_family_diff.sort(key=lambda d: d.members_diff)
    tokens_family_diff.sort(key=lambda d: d.members_diff)

    heads_coverage_diff = compute_coverage_diff(heads_family_diff, source,
            resource_pk, progress_monitor)
    tokens_coverage_diff = compute_coverage_diff(tokens_family_diff, source,
            resource_pk, progress_monitor)

    progress_monitor.info('Sorting coverage diff')
    heads_coverage_diff.sort(key=lambda d: d.coverage_diff)
    tokens_coverage_diff.sort(key=lambda d: d.coverage_diff)

    report_diff(heads_family_diff, heads_coverage_diff, 'Head Report')

    report_diff(tokens_family_diff, tokens_coverage_diff, 'Token Report')

    report_add_remove(removed, added)


def compute_family_index(codebase, progress_monitor):
    heads = defaultdict(list)
    tokens = defaultdict(list)

    families = cmodel.CodeElementFamily.objects.filter(codebase=codebase)
    progress_monitor.start('Computing family index for codebase {0}'
            .format(codebase), families.count())

    for family in families.all():
        if family.head is not None:
            heads[family.head.human_string()].append(family)
        else:
            tokens[family.token].append(family)
        progress_monitor.work('Computed a family index', 1)

    progress_monitor.done()

    return (heads, tokens)


def compute_family_diff(index_from, index_to, added, removed,
        progress_monitor):
    processed = set()
    family_diffs = []
    progress_monitor.start('Computing family diff', len(index_from))

    for key in index_from:
        for family_from in index_from[key]:
            family_to = get_family(family_from, index_to, key)
            if family_to is None:
                removed.append(family_from)
            else:
                diff = cmodel.FamilyDiff(family_from, family_to)
                family_diffs.append(diff)
                processed.add(family_to.pk)
        progress_monitor.work('Computed family diffs', 1)

    progress_monitor.info('Computing added families')

    for families_to in index_to.values():
        for family_to in families_to:
            if family_to.pk not in processed:
                added.append(family_to)

    progress_monitor.done()

    return family_diffs


def compute_coverage_diff(family_diffs, source, resource_pk, progress_monitor):
    coverage_diffs = []

    progress_monitor.start('Computing coverage diff', len(family_diffs))

    for family_diff in family_diffs:
        coverage_from = family_diff.family_from.get_coverage(source,
                resource_pk)
        coverage_to = family_diff.family_to.get_coverage(source,
                resource_pk)
        if coverage_from is None or coverage_to is None:
            progress_monitor.info('ERROR! One coverage is none: {0} {1}'
                    .format(family_diff.family_from.pk,
                        family_diff.family_to.pk))
            progress_monitor.work('Skipping coverage diff', 1)
            continue
        elif not coverage_from.is_interesting():
            continue

        diff = cmodel.CoverageDiff(coverage_from, coverage_to)
        coverage_diffs.append(diff)
        progress_monitor.work('Computing coverage diff', 1)

    progress_monitor.done()

    return coverage_diffs


def report_diff(family_diffs, coverage_diffs, report_title):
    top = 25
    print()
    print(report_title)
    print('\nREPORTING TOP {0} FAMILY DIFFS\n'.format(top))
    print('Total Family Diffs: {0}'.format(len(family_diffs)))
    for family_diff in family_diffs[:top]:
        print('{0}: From: {1}[{2}]  To: {3} [{4}]'.
                format(family_diff.members_diff, family_diff.family_from,
                    family_diff.family_from.pk, family_diff.family_to,
                    family_diff.family_to.pk))

    print('\nREPORTING TOP {0} COVERAGE DIFFS\n'.format(top))
    print('Total coverage diffs: {0}'.format(len(coverage_diffs)))
    for cov_diff in coverage_diffs[:top]:
        print('{0}: From: {1}[{2}]  To: {3} [{4}]'.
                format(cov_diff.coverage_diff, cov_diff.coverage_from,
                    cov_diff.coverage_from.pk, cov_diff.coverage_to,
                    cov_diff.coverage_to.pk))
        report_location(cov_diff.coverage_from)

    print()


def report_location(coverage):
    for member in coverage.family.members.all():
        for link in member.potential_links.filter(index=0).all():
            if link.code_reference.resource_object_id ==\
                coverage.resource_object_id and link.code_reference.source ==\
                coverage.source:
                print('  {0} in {1}/{2}'.format(member.human_string(),
                    link.code_reference.local_context,
                    link.code_reference.global_context))


def report_add_remove(removed, added):
    top = 25
    print()
    print('REPORTING TOP {0} REMOVED FAMILIES\n'.format(top))
    for family in removed[:top]:
        print('{0}: {1}[{2}]'.format(family.members.count(), family,
            family.pk))

    print('REPORTING TOP {0} ADDED FAMILIES\n'.format(top))
    for family in added[:top]:
        print('{0}: {1}[{2}]'.format(family.members.count(), family,
            family.pk))


def get_family(family, index, key):
    if key not in index:
        return None
    else:
        for temp_family in index[key]:
            if family.equiv(temp_family):
                return temp_family
    return None

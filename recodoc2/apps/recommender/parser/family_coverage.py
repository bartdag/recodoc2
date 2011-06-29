from __future__ import unicode_literals
from collections import defaultdict
import codebase.models as cmodel
import recommender.models as rmodel
import codebase.linker.context as ctx
from docutil.progress_monitor import NullProgressMonitor, CLIProgressMonitor
from docutil.str_util import tokenize
from docutil.commands_util import size


SUPER_REC_THRESHOLD = 0.2

LOCATION_THRESHOLD = 0.5


def create_family(head, codebase, criterion, first_criterion):
    family = rmodel.CodeElementFamily(head=head)
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
                        rmodel.DECLARATION, first_criterion)
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
                        rmodel.HIERARCHY, first_criterion)
            families1[pk].members.add(code_element)

        # Hierarchy D
        ancestors_list = ctx.get_ancestors_value(code_element)
        ancestors = {ancestor.pk: ancestor for ancestor in ancestors_list}

        for ancestor_pk in ancestors:
            if ancestor_pk not in familiesd:
                familiesd[ancestor_pk] = create_family(
                        ancestors[ancestor_pk],
                        code_element.codebase,
                        rmodel.HIERARCHY_D,
                        first_criterion)
            familiesd[ancestor_pk].members.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return (families1, familiesd)


def compute_no_abstract_family(families,
        progress_monitor=NullProgressMonitor()):

    new_families = {}
    progress_monitor.start('Comp. No Abstract Families', len(families))

    for head_pk in families:
        family = families[head_pk]
        code_elements = family.members.all()
        new_members = [code_element for code_element in code_elements if
                not code_element.abstract]
        new_size = len(new_members)
        if new_size > 0 and new_size < family.members.count():
            new_family = create_family(family.head, family.codebase,
                    rmodel.NO_ABSTRACT, False)
            new_family.criterion1 = family.criterion1
            new_family.save()
            new_family.members.add(*new_members)
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
    progress_monitor.start('Processing {0} token for code elements'
            .format(len(tokens)), len(tokens))
   
    progress_monitor.info('Computing code element names')
    ctokens = []
    for code_element in code_elements.all():
        name = code_element.simple_name.lower().strip()
        element_tokens = [token.lower().strip() for token in
                tokenize(code_element.simple_name)]
        ctokens.append((name, code_element, element_tokens))
    progress_monitor.info('Computed code element names')

    for token in tokens:
        start = defaultdict(list)
        end = defaultdict(list)
        middle = defaultdict(list)

        if first_criterion:
            addt = lambda d, e: d[e.kind.pk].append(e)
        else:
            addt = lambda d, e: d[0].append(e)

        for (name, code_element, element_tokens) in ctokens:

            if token not in element_tokens:
                continue
            elif name.startswith(token):
                addt(start, code_element)
            elif name.endswith(token):
                addt(end, code_element)
            elif name.find(token) > -1:
                addt(middle, code_element)

        #print('Debugging {0}: {1} {2} {3}'.format(token, len(start), len(end),
            #len(middle)))
            
        for start_members in start.values():
            if len(start_members) > 1:
                family = create_family(None, codebase, rmodel.TOKEN,
                        first_criterion)
                family.token = token
                family.token_pos = rmodel.PREFIX
                family.save()
                family.members.add(*start_members)
                families[family.pk] = family
                if first_criterion:
                    family.kind = start_members[0].kind
                    family.save()

        for end_members in end.values():
            if len(end_members) > 1:
                family = create_family(None, codebase, rmodel.TOKEN,
                        first_criterion)
                family.token = token
                family.token_pos = rmodel.SUFFIX
                family.save()
                family.members.add(*end_members)
                families[family.pk] = family
                if first_criterion:
                    family.kind = end_members[0].kind
                    family.save()

        for mid_members in middle.values():
            if len(mid_members) > 1:
                family = create_family(None, codebase, rmodel.TOKEN,
                        first_criterion)
                family.token = token
                family.token_pos = rmodel.MIDDLE
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

        fam_coverage = rmodel.FamilyCoverage(family=family, resource=resource,
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

    families = rmodel.CodeElementFamily.objects.filter(codebase=codebase)
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
                diff = rmodel.FamilyDiff(family_from=family_from,
                        family_to=family_to)
                diff.compute_diffs()
                diff.save()
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

        diff = rmodel.CoverageDiff(coverage_from=coverage_from,
                coverage_to=coverage_to)
        diff.compute_diffs()
        diff.save()
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


def compute_coverage_recommendation(coverage_diffs,
        progress_monitor=NullProgressMonitor()):

    recommendations = []
    diffs_len = size(coverage_diffs)
    progress_monitor.start('Processing {0} diffs'.format(diffs_len),
            diffs_len)

    for coverage_diff in coverage_diffs:
        (covered_mem_from, uncovered_mem_from) =\
            get_members(coverage_diff.coverage_from)
        (_, uncovered_mem_to) = get_members(coverage_diff.coverage_to)

        members_to_doc = []
        for member_key in uncovered_mem_to:
            if member_key not in covered_mem_from and \
                    member_key not in uncovered_mem_from:
                members_to_doc.append(uncovered_mem_to[member_key])

        if len(members_to_doc) > 0:
            recommendation = rmodel.AddRecommendation(
                    coverage_diff=coverage_diff)
            recommendation.save()
            recommendation.new_members.add(*members_to_doc)
            recommendation.old_members.add(*covered_mem_from.values())
            recommendations.append(recommendation)

        progress_monitor.work('Processed diff', 1)

    progress_monitor.done()

    return recommendations


def get_members(fam_coverage):
    family = fam_coverage.family
    pk = fam_coverage.resource_object_id
    source = fam_coverage.source
    covered_members = {}
    uncovered_members = {}

    for member in family.members.all():
        if cmodel.CodeElementLink.objects.\
                filter(code_element=member).\
                filter(index=0).\
                filter(code_reference__resource_object_id=pk).\
                filter(code_reference__source=source).exists():
            covered_members[member.human_string()] = member
        else:
            uncovered_members[member.human_string()] = member

    return (covered_members, uncovered_members)


def compute_super_recommendations(recommendations,
        progress_monitor=NullProgressMonitor()):

    recommendations.sort(key=lambda r: r.new_members.count(), reverse=True)
    processed_recs = set()
    super_recs = []

    reclen = len(recommendations)
    progress_monitor.start('Processing {0} recommendations'.format(reclen),
            reclen)
    
    for i, rec in enumerate(recommendations):
        if rec.pk in processed_recs:
            continue
            progress_monitor.work('Skipped rec', 1)

        processed_recs.add(rec.pk)
        super_rec = rmodel.SuperAddRecommendation(initial_rec=rec,
                codebase_from=rec.coverage_diff.coverage_from.family.codebase,
                codebase_to=rec.coverage_diff.coverage_to.family.codebase,
                resource=rec.coverage_diff.coverage_from.resource,
                source=rec.coverage_diff.coverage_from.source)
        super_rec.save()
        super_rec.recommendations.add(rec)
        super_recs.append(super_rec)
        new_members = list(rec.new_members.all())
        count = float(len(new_members))
        
        for temprec in recommendations[i+1:]:
            if (1.0 - (temprec.new_members.count() / count)) > \
                    SUPER_REC_THRESHOLD:
                break
            if proper_subset(list(temprec.new_members.all()), new_members):
                super_rec.recommendations.add(temprec)
                processed_recs.add(temprec.pk)
        
        super_rec.best_rec =\
            get_best_rec(list(super_rec.recommendations.all()))
        super_rec.save()

        progress_monitor.work('Processed rec', 1)

    progress_monitor.done()

    sort_super_recs(super_recs)
    for i, super_rec in enumerate(super_recs):
        super_rec.index = i
        super_rec.save()

    return super_recs


def proper_subset(members1, members2):
    members1set = {member.human_string() for member in members1}
    members2set = {member.human_string() for member in members2}
    return members1set <= members2set


def get_best_rec(recommendations):
    def snd_crit(rec):
        fam = rec.coverage_diff.coverage_from.family
        if fam.criterion2 is None:
            return 1
        else:
            return 0
    def fst_crit(rec):
        fam = rec.coverage_diff.coverage_from.family
        if fam.criterion1 == rmodel.TOKEN:
            return 0
        else:
            return 1
    def cvr(rec):
        return rec.coverage_diff.coverage_from.coverage

    recommendations.sort(key=snd_crit, reverse=True)
    recommendations.sort(key=fst_crit, reverse=True)
    recommendations.sort(key=cvr, reverse=True)

    return recommendations[0]

def sort_super_recs(super_recommendations):
    def snd_crit(super_rec):
        fam = super_rec.best_rec.coverage_diff.coverage_from.family
        if fam.criterion2 is None:
            return 1
        else:
            return 0
    def fst_crit(super_rec):
        fam = super_rec.best_rec.coverage_diff.coverage_from.family
        if fam.criterion1 == rmodel.TOKEN:
            return 0
        else:
            return 1
    def cvr(super_rec):
        return super_rec.best_rec.coverage_diff.coverage_from.coverage

    super_recommendations.sort(key=snd_crit, reverse=True)
    super_recommendations.sort(key=fst_crit, reverse=True)
    super_recommendations.sort(key=cvr, reverse=True)


def report_super(super_recs):
    for super_rec in super_recs:
        (sections, pages, section_spread, page_spread) = \
                get_locations(super_rec)

        print('\nSUPER REC: {0}'.format(super_rec))
        for member in super_rec.best_rec.new_members.all():
            print('  to document: {0}'.format(member.human_string()))

        print('\n  Important Pages:')
        for (page, members) in pages:
            old_count = super_rec.best_rec.old_members.count()
            covered = len(members)
            print('    {0}: {1} / {2}'.format(page.title, covered, old_count))
            #for member in members:
                #print('      {0}'.format(member.human_string()))
        if page_spread:
            print('  New members will probably be added in new pages')

        print('\n  Important Sections:')
        for (section, members) in sections:
            old_count = super_rec.best_rec.old_members.count()
            covered = len(members)
            print('    {0}: {1} / {2}'.format(section.title, covered, old_count))
            #for member in members:
                #print('      {0}'.format(member.human_string()))
        if section_spread:
            print('  New members will probably be added in new sections')

        for rec in super_rec.recommendations.all():
            print('  subrec: {0}'.format(rec))


def get_locations(super_rec):
    sections = ()
    pages = ()
    section_spread = False
    page_spread = False
    
    sections_objects = {}
    pages_objects = {}

    sectionsd = defaultdict(list)
    pagesd = defaultdict(list)

    resource_pk = super_rec.resource_object_id
    source = super_rec.source

    count = 0

    for member in super_rec.best_rec.old_members.all():
        visited_sections = set()
        visited_pages = set()
        for link in member.potential_links.filter(index=0).all():
            if link.code_reference.resource_object_id == resource_pk and\
                    link.code_reference.source == source:
                section = link.code_reference.local_context
                page = link.code_reference.global_context
                if section.pk not in visited_sections:
                    sections_objects[section.pk] = section
                    sectionsd[section.pk].append(member)
                    visited_sections.add(section.pk)

                if page.pk not in visited_pages:
                    pages_objects[page.pk] = page
                    pagesd[page.pk].append(member)
                    visited_pages.add(page.pk)

        count += 1

    sections = [(sections_objects[pk], sectionsd[pk]) for pk in sectionsd]
    pages = [(pages_objects[pk], pagesd[pk]) for pk in pagesd]

    # Sort them
    sections.sort(key=lambda v: len(v[1]), reverse=True)
    pages.sort(key=lambda v: len(v[1]), reverse=True)

    section_spread = (len(sections[0][1]) / float(count)) < LOCATION_THRESHOLD
    page_spread = (len(pages[0][1]) / float(count)) < LOCATION_THRESHOLD

    return (sections, pages, section_spread, page_spread)

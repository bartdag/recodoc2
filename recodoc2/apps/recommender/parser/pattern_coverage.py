from __future__ import unicode_literals
from collections import defaultdict
import codebase.models as cmodel
import recommender.models as rmodel
import codebase.linker.context as ctx
from docutil.progress_monitor import NullProgressMonitor, CLIProgressMonitor
from docutil.str_util import tokenize
from docutil.commands_util import size


SUPER_REC_THRESHOLD = 0.4

LOCATION_THRESHOLD = 0.5

OVERLOADED_THRESHOLD = 0.5

VALID_COVERAGE_THRESHOLD = 0.5


def create_pattern(head, codebase, criterion, first_criterion):
    pattern = rmodel.CodePattern(head=head)
    if first_criterion:
        pattern.criterion1 = criterion
    else:
        pattern.criterion2 = criterion
    pattern.codebase = codebase
    pattern.save()

    return pattern


def compute_declaration_pattern(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    '''Go through all code element and insert it in a pattern represented by
       its container.
    '''
    patterns = {}

    progress_monitor.start('Comp. Declaration patterns', size(code_elements))

    for code_element in code_elements:
        kind_pk = code_element.kind.pk
        for container in code_element.containers.all():
            pk = container.pk
            key = '{0}-{1}'.format(pk, kind_pk)
            if key not in patterns:
                patterns[key] = create_pattern(container, container.codebase,
                        rmodel.DECLARATION, first_criterion)
                patterns[key].kind = code_element.kind
                patterns[key].save()
            patterns[key].extension.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return patterns


def compute_ancestors(code_element, ancestors):
    for parent in code_element.parents.all():
        if parent.pk not in ancestors:
            ancestors[parent.pk] = parent
            compute_ancestors(parent, ancestors)


def compute_hierarchy_pattern(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    '''Go through all code elements and insert it in a pattern represented by
       its direct container. Then, insert it in a pattern represented by any of
       its ancestor.
    '''
    patterns1 = {}
    patternsd = {}

    progress_monitor.start('Comp. Hierarchy Patterns', size(code_elements))

    for code_element in code_elements:
        # Hierarchy 1
        for parent in code_element.parents.all():
            pk = parent.pk
            if pk not in patterns1:
                patterns1[pk] = create_pattern(parent, parent.codebase,
                        rmodel.HIERARCHY, first_criterion)
            patterns1[pk].extension.add(code_element)

        # Hierarchy D
        ancestors_list = ctx.get_ancestors_value(code_element)
        ancestors = {ancestor.pk: ancestor for ancestor in ancestors_list}

        for ancestor_pk in ancestors:
            if ancestor_pk not in patternsd:
                patternsd[ancestor_pk] = create_pattern(
                        ancestors[ancestor_pk],
                        code_element.codebase,
                        rmodel.HIERARCHY_D,
                        first_criterion)
            patternsd[ancestor_pk].extension.add(code_element)

        progress_monitor.work('Code Element processed', 1)

    progress_monitor.done()

    return (patterns1, patternsd)


def compute_no_abstract_pattern(patterns,
        progress_monitor=NullProgressMonitor()):
    '''Go through all patterns. If a proper subset of the patterns is non
       abstract, create a new pattern, with non-abstract as a second criteria.
    '''

    new_patterns = {}
    progress_monitor.start('Comp. No Abstract patterns', len(patterns))

    for head_pk in patterns:
        pattern = patterns[head_pk]
        code_elements = pattern.extension.all()
        new_extension = [code_element for code_element in code_elements if
                not code_element.abstract]
        new_size = len(new_extension)
        if new_size > 0 and new_size < pattern.extension.count():
            new_pattern = create_pattern(pattern.head, pattern.codebase,
                    rmodel.NO_ABSTRACT, False)
            new_pattern.criterion1 = pattern.criterion1
            new_pattern.save()
            new_pattern.extension.add(*new_extension)
            new_patterns[new_pattern.pk] = new_pattern
        progress_monitor.work('pattern processed', 1)

    progress_monitor.done()

    return new_patterns


def compute_token_pattern_second(patterns,
        progress_monitor=NullProgressMonitor()):
    '''For each pattern, compute sub patterns based on token.'''

    progress_monitor.start('Computing token for a set of patterns',
            len(patterns))
    token_patterns = {}

    for head_pk in patterns:
        pattern = patterns[head_pk]
        code_elements = pattern.extension.all()
        sub_patterns = compute_token_pattern(code_elements, False,
                CLIProgressMonitor())
        for key in sub_patterns:
            sub_pattern = sub_patterns[key]
            sub_pattern.head = pattern.head
            sub_pattern.criterion1 = pattern.criterion1
            sub_pattern.save()
            token_patterns[sub_pattern.pk] = sub_pattern
        progress_monitor.work('pattern processed.', 1)

    progress_monitor.done()

    return token_patterns


def compute_tokens(code_elements):
    '''Compute a set of all tokens contained in the provided code elements.'''
    tokens = set()
    for code_element in code_elements.all():
        temp = [token.lower().strip() for token in
                tokenize(code_element.simple_name)]
        tokens.update(temp)
    return tokens


def compute_token_pattern(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    '''For each token, go through all code elements and create three patterns:
       code elements that start with a token, elements that end with a token,
       and elements that have the token in the middle. This is exclusive.
    '''
    patterns = {}
    if size(code_elements) == 0:
        return patterns

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
            # Here, we want to avoid mixing classes with methods and fields!
            addt = lambda d, e: d[e.kind.pk].append(e)
        else:
            # Here, we already know that they are part of the same pattern, so
            # they don't mix.
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

        for start_extension in start.values():
            if len(start_extension) > 1:
                pattern = create_pattern(None, codebase, rmodel.TOKEN,
                        first_criterion)
                pattern.token = token
                pattern.token_pos = rmodel.PREFIX
                pattern.save()
                pattern.extension.add(*start_extension)
                patterns[pattern.pk] = pattern
                if first_criterion:
                    pattern.kind = start_extension[0].kind
                    pattern.save()

        for end_extension in end.values():
            if len(end_extension) > 1:
                pattern = create_pattern(None, codebase, rmodel.TOKEN,
                        first_criterion)
                pattern.token = token
                pattern.token_pos = rmodel.SUFFIX
                pattern.save()
                pattern.extension.add(*end_extension)
                patterns[pattern.pk] = pattern
                if first_criterion:
                    pattern.kind = end_extension[0].kind
                    pattern.save()

        for mid_extension in middle.values():
            if len(mid_extension) > 1:
                pattern = create_pattern(None, codebase, rmodel.TOKEN,
                        first_criterion)
                pattern.token = token
                pattern.token_pos = rmodel.MIDDLE
                pattern.save()
                pattern.extension.add(*mid_extension)
                patterns[pattern.pk] = pattern
                if first_criterion:
                    pattern.kind = mid_extension[0].kind
                    pattern.save()

        progress_monitor.work('Processed a token')
    progress_monitor.done()
    return patterns


def compute_coverage(patterns, source, resource,
        progress_monitor=NullProgressMonitor):
    '''For each pattern, compute coverage (linked elements / total elements).
    '''

    progress_monitor.start('Computing Coverage', size(patterns))

    for pattern in patterns.all():
        total = pattern.extension.count()
        count = 0
        pk = resource.pk
        for member in pattern.extension.all():
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

        pat_coverage = rmodel.CodePatternCoverage(pattern=pattern,
                resource=resource, source=source, coverage=coverage)
        pat_coverage.save()
        progress_monitor.work('Processed a pattern', 1)

    progress_monitor.done()


def filter_coverage(patterns_query):
    patterns_query.filter(coverage__lt=VALID_COVERAGE_THRESHOLD).\
            update(valid=False)


def combine_coverage(coverages, progress_monitor=NullProgressMonitor()):

    coverages_list = list(coverages.all())
    coverages_list.sort(key=lambda c: c.pattern.extension.count(),
            reverse=True)
    doc_patterns = []
    processed_coverage = set()
    cov_len = len(coverages_list)
    progress_monitor.start('Processing {0} patterns'.format(cov_len), cov_len)

    for i, coverage in enumerate(coverages_list):
        if coverage.pk in processed_coverage:
            progress_monitor.work('Skipped pattern', 1)
            continue

        current_best_cov = coverage.coverage
        processed_coverage.add(coverage)
        doc_pattern = rmodel.DocumentationPattern()
        doc_pattern.save()
        doc_pattern.patterns.add(coverage)
        doc_patterns.append(doc_pattern)
        extension = list(coverage.pattern.extension.all())
        count = float(len(extension))

        for tempcoverage in coverages_list[i + 1:]:
            tempcoverage_value = tempcoverage.coverage
            if (1.0 - (tempcoverage.pattern.extension.count() / count)) > \
                    SUPER_REC_THRESHOLD:
                # We are too much different in terms of members
                # Go to next
                if tempcoverage_value > current_best_cov:
                    # This temp coverage has a better coverage than me, start
                    # a new doc pattern. There is no way the next will be
                    # included in this one.
                    # XXX Is this step even necessary?
                    break
            if proper_subset(list(tempcoverage.pattern.extension.all()),
                    extension):
                if tempcoverage_value > current_best_cov:
                    current_best_cov = tempcoverage_value
                doc_pattern.patterns.add(tempcoverage)
                processed_coverage.add(tempcoverage.pk)

        doc_pattern.main_pattern = \
            get_best_pattern(list(doc_pattern.patterns.all()))
        doc_pattern.save()

        progress_monitor.work('Processed documentation pattern', 1)

    progress_monitor.info('Created {0} documentation patterns'.
            format(len(doc_patterns)))
    progress_monitor.done()

    return doc_patterns


def get_best_pattern(coverages):

    def snd_crit(coverage):
        pattern = coverage.pattern
        if pattern.criterion2 is None:
            return 1
        else:
            return 0

    def fst_crit(coverage):
        pattern = coverage.pattern
        if pattern.criterion1 == rmodel.TOKEN:
            return 0
        else:
            return 1

    def cvr(coverage):
        return coverage.coverage

    # For equal coverage and token/no token, favor no second criterion.
    coverages.sort(key=snd_crit, reverse=True)
    # For equal coverage, favor non-token Second.
    coverages.sort(key=fst_crit, reverse=True)
    # Favor coverage First.
    coverages.sort(key=cvr, reverse=True)

    return coverages[0]


def compare_coverage(codebase_from, codebase_to, source, resource_pk,
        progress_monitor=NullProgressMonitor):
    '''First, match head-based (declaration/hierarchy) and token-based
       families.
       Then, for each matched family, compare their coverage.
    '''

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
    removed.sort(key=lambda f: f.extension.count(), reverse=True)
    added.sort(key=lambda f: f.extension.count(), reverse=True)

    progress_monitor.info('Sorting family diff')
    heads_family_diff.sort(key=lambda d: d.extension_diff)
    tokens_family_diff.sort(key=lambda d: d.extension_diff)

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
    '''Compute an index of the families based on their head or token.'''
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
    '''For each index and each family, try to find a matching family based on
       family.equiv.
    '''
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
    '''For each family, get the coverage related to a particular resource.
       Note: a family in a codebase could have coverage for more than one
       document (especially during experimentation/evaluation :-) ).
    '''
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
                format(family_diff.extension_diff, family_diff.family_from,
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
    for member in coverage.family.extension.all():
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
        print('{0}: {1}[{2}]'.format(family.extension.count(), family,
            family.pk))

    print('REPORTING TOP {0} ADDED FAMILIES\n'.format(top))
    for family in added[:top]:
        print('{0}: {1}[{2}]'.format(family.extension.count(), family,
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
    '''For each coverage diff, check if there is at least one new element in a
       family that was not there before (release 1) and that is not documented
       now (release 2).

       For each such coverage diff, create a recommendation.
    '''

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
    '''Combine similar recommendations together.
       Recommendations are combined if there isn't more than 20% difference and
       one is a proper subset of the other.
    '''

    recommendations.sort(key=lambda r: r.new_members.count(), reverse=True)
    processed_recs = set()
    super_recs = []

    reclen = len(recommendations)
    progress_monitor.start('Processing {0} recommendations'.format(reclen),
            reclen)

    for i, rec in enumerate(recommendations):
        if rec.pk in processed_recs:
            progress_monitor.work('Skipped rec', 1)
            continue

        current_best_cov = rec.coverage_diff.coverage_from.coverage
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

        for temprec in recommendations[i + 1:]:
            coverage_from = temprec.coverage_diff.coverage_from.coverage
            if (1.0 - (temprec.new_members.count() / count)) > \
                    SUPER_REC_THRESHOLD:
                if coverage_from > current_best_cov:
                    break
            if proper_subset(list(temprec.new_members.all()), new_members):
                if coverage_from > current_best_cov:
                    current_best_cov = coverage_from
                super_rec.recommendations.add(temprec)
                processed_recs.add(temprec.pk)

        super_rec.best_rec =\
            get_best_rec(list(super_rec.recommendations.all()))
        check_overloading(super_rec)
        super_rec.save()

        progress_monitor.work('Processed rec', 1)

    progress_monitor.done()

    sort_super_recs(super_recs)
    for i, super_rec in enumerate(super_recs):
        super_rec.index = i
        super_rec.save()

    return super_recs


def check_overloading(super_rec):
    '''We don't want to recommend a new method that is an overloaded version of
       an already covered method.'''
    overloaded = 0
    total = 0
    for member in super_rec.best_rec.new_members.all():
        total += 1
        codebase = member.codebase
        if member.kind.kind != 'method':
            continue
        if codebase.code_elements.filter(fqn=member.fqn).count() > 1:
            overloaded += 1
    if float(overloaded) / float(total) > OVERLOADED_THRESHOLD:
        super_rec.overloaded = True


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

        if super_rec.overloaded:
            print('\n  **Overloaded recommendation**')

        print('\n  Important Pages:')
        for (page, members) in pages:
            old_count = super_rec.best_rec.old_members.count()
            covered = len(members)
            print('    {0}: {1} / {2}'.format(page.title, covered, old_count))
            #for member in members:
                #print('      {0}'.format(member.human_string()))
        if page_spread:
            print('\n  **New members will probably be added in new pages**')

        print('\n  Important Sections:')
        for (section, members) in sections:
            old_count = super_rec.best_rec.old_members.count()
            covered = len(members)
            print('    {0}: {1} / {2}'.format(section.title,
                covered, old_count))
            #for member in members:
                #print('      {0}'.format(member.human_string()))
        if section_spread:
            print('\n  **New members will probably be added in new sections**')

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

from __future__ import unicode_literals
from django.db import connection
from django.contrib.contenttypes.models import ContentType
from docutil.progress_monitor import CLIProgressMonitor
from docutil.commands_util import get_content_type, dictfetchall
from docutil.str_util import normalize
from project.models import ProjectRelease
from codebase.models import CodeBase, CodeElementLink, CodeElement
from recommender.models import CodePattern, CodePatternCoverage,\
        DocumentationPattern,\
        CoverageDiff, SuperAddRecommendation, RemoveRecommendation,\
        HighLink, CodeLink
import recommender.parser.pattern_coverage as pcoverage


SRC_SNIPPET_QUERY = 'AND code1.snippet_id is NULL'

DST_SNIPPET_QUERY = 'AND code2.snippet_id is NULL'

SUB_QUERIES="""
WITH scts AS (
    SELECT code1.local_object_id as section_id,
           link1.code_element_id as section_code_id
    FROM codebase_singlecodereference as code1, 
         codebase_codeelementlink as link1, 
         codebase_codeelement as ce1
    WHERE link1.index=0 AND link1.code_reference_id = code1.id AND
          link1.code_element_id = ce1.id AND
          ce1.codebase_id = {codebase_id} AND
          code1.resource_object_id={src_resource_id} AND
          code1.{src_type_type}_content_type_id={src_content_type}
          {src_snippet_query}
    GROUP BY code1.{src_type_type}_object_id, link1.code_element_id
    ),

    msgs AS (
    SELECT code2.local_object_id as msg_id, 
           link2.code_element_id as msg_code_id
    FROM codebase_singlecodereference as code2, 
         codebase_codeelementlink as link2, 
         codebase_codeelement as ce2
    WHERE link2.index=0 AND link2.code_reference_id = code2.id AND
          link2.code_element_id = ce2.id AND
          ce2.codebase_id = {codebase_id} AND
          code2.resource_object_id={dst_resource_id} AND
          code2.{dst_type_type}_content_type_id={dst_content_type}
          {dst_snippet_query}
    GROUP BY code2.{src_type_type}_object_id, link2.code_element_id
    ),

    common AS (
    SELECT scts.section_id AS section_id,
           msgs.msg_id AS msg_id,
           scts.section_code_id as code_id
    FROM scts, msgs
    WHERE scts.section_code_id = msgs.msg_code_id
    ),

    common_size AS (
    SELECT scts.section_id AS section_id,
           msgs.msg_id AS msg_id,
           COUNT(scts.section_code_id) as size
    FROM scts, msgs
    WHERE scts.section_code_id = msgs.msg_code_id
    GROUP BY scts.section_id, msgs.msg_id
    ),
    
    main AS (
    SELECT common.section_id as section_id,
           common.msg_id as msg_id,
           common.code_id as code_id,
           common_size.size as size
    FROM common, common_size
    WHERE common.section_id = common_size.section_id AND
          common.msg_id = common_size.msg_id
    ORDER BY section_id, msg_id, code_id
    )
"""

MAIN_QUERY="""
SELECT section_id, msg_id, code_id, size
FROM main
WHERE size > {size}
ORDER BY msg_id, section_id, code_id
"""




def compute_patterns(pname, bname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    code_elements = codebase.code_elements.all()

    progress_monitor = CLIProgressMonitor(min_step=1.0)

    dpatterns = pcoverage.compute_declaration_pattern(code_elements, True,
            progress_monitor)
    (hpatterns1, hpatternsd) = pcoverage.\
            compute_hierarchy_pattern(code_elements, True, progress_monitor)

    pcoverage.compute_no_abstract_pattern(dpatterns, progress_monitor)
    pcoverage.compute_no_abstract_pattern(hpatterns1, progress_monitor)
    pcoverage.compute_no_abstract_pattern(hpatternsd, progress_monitor)

    pcoverage.compute_token_pattern_second(dpatterns, progress_monitor)

    pcoverage.compute_token_pattern(code_elements, True, progress_monitor)


def clear_patterns(pname, bname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    CodePattern.objects.filter(codebase=codebase).delete()


def filter_patterns(pname, bname, release, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]

    coverages = CodePatternCoverage.objects.\
            filter(pattern__codebase=codebase1).filter(source=source).\
            filter(resource_object_id=resource_pk)

    pcoverage.filter_coverage(coverages)


def combine_patterns(pname, bname, release, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]

    coverages = CodePatternCoverage.objects.\
            filter(pattern__codebase=codebase1).filter(source=source).\
            filter(resource_object_id=resource_pk).filter(valid=True)

    progress_monitor = CLIProgressMonitor(min_step=1.0)

    pcoverage.combine_coverage(coverages, progress_monitor)


def doc_patterns_location(pname, bname, release, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]

    doc_patterns = DocumentationPattern.objects.\
            filter(main_pattern__pattern__codebase=codebase1).\
            filter(main_pattern__source=source).\
            filter(main_pattern__resource_object_id=resource_pk).\
            filter(main_pattern__valid=True)

    for doc_pattern in doc_patterns:
        pcoverage.compute_doc_pattern_location(doc_pattern)


def report_doc_patterns(pname, bname, release, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]

    doc_patterns = DocumentationPattern.objects.\
            filter(main_pattern__pattern__codebase=codebase1).\
            filter(main_pattern__source=source).\
            filter(main_pattern__resource_object_id=resource_pk).\
            filter(main_pattern__valid=True).order_by('-main_pattern__coverage')

    for i, doc_pattern in enumerate(doc_patterns.iterator()):
        print('{0}. DOCUMENTATION PATTERN'.format(i))
        pk = doc_pattern.main_pattern.pk
        print('MAIN PATTERN')
        report_single_coverage(doc_pattern.main_pattern)
        print('LOC:')
        report_location(doc_pattern)

        for coverage in doc_pattern.patterns.all():
            if coverage.pk == pk:
                continue
            print('SUB PATTERN')
            report_single_coverage(coverage)
        print('')


def report_single_coverage(coverage):
    print('  coverage: {0}'.format(coverage.coverage))
    print('  Intension:\n  {0}'.format(coverage.pattern))
    print('  Extension:')
    (member_locations, _, _) = pcoverage.get_locations_coverage(coverage)
    for member in coverage.pattern.extension.all():
        print('    {0}'.format(member))
        (sections, pages) = member_locations[member.pk]
        for section in sections:
            print('      Section: {0}'.format(section))
        for page in pages:
            print('      Page: {0}'.format(page))
    print('')


def report_location(doc_pattern):
    for location in doc_pattern.doc_pattern_locations.all():
        if location.single_section:
            print('  Section: {0} ({1}) - {2}'.format(
                location.location.location, location.location.location.page,
                location.coverage))
        elif location.single_page:
            print('  Page: {0} - {1}'.format(location.location.location,
                location.coverage))
        elif location.multi_page:
            for loc in location.locations.all():
                print('  MultiPage: {0}'.format(loc.location))
    print('')


def find_high_level_links_msg(pname, bname, release, pk_resource_src,
        pk_resource_dst, msg_level, no_snippet, size):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]

    if msg_level:
        dst_type = ContentType.objects.get(app_label="channel",
                model="message").pk
        src_type = ContentType.objects.get(app_label="doc",
                model="section").pk
        src_type_type = dst_type_type = 'local'
    else:
        dst_type = ContentType.objects.get(app_label="channel",
                model="supportthread").pk
        src_type = ContentType.objects.get(app_label="doc",
                model="page").pk
        src_type_type = dst_type_type = 'global'

    if no_snippet:
        src_snippet = SRC_SNIPPET_QUERY
        dst_snippet = DST_SNIPPET_QUERY
    else:
        src_snippet = ''
        dst_snippet = ''

    params = {
        'codebase_id': codebase.pk,
        'src_resource_id': pk_resource_src,
        'src_type_type': src_type_type,
        'src_content_type': src_type,
        'dst_resource_id': pk_resource_dst,
        'dst_type_type': dst_type_type,
        'dst_content_type': dst_type,
        'src_snippet_query': src_snippet,
        'dst_snippet_query': dst_snippet,
    }
    sub_query = SUB_QUERIES.format(**params)
    main = sub_query + MAIN_QUERY.format(size=size)

    cursor = connection.cursor()
    cursor.execute(main)
    result = dictfetchall(cursor)

    (msg_index, section_index, code_index) = index_high_level_links(result,
            src_type, dst_type)
    report_msg_high_level(msg_index)
    report_section_high_level(section_index)
    report_code_high_level(code_index)

    return result


def compare_coverage(pname, bname, release1, release2, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    progress_monitor = CLIProgressMonitor(min_step=1.0)

    pcoverage.compare_coverage(codebase1, codebase2, source, resource_pk,
            progress_monitor)


def compute_addition_reco(pname, bname, release1, release2, source,
        resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    coverage_diffs = CoverageDiff.objects.\
            filter(coverage_from__resource_object_id=resource_pk).\
            filter(coverage_from__source=source).\
            filter(coverage_from__pattern__codebase=codebase1).\
            filter(coverage_to__resource_object_id=resource_pk).\
            filter(coverage_to__source=source).\
            filter(coverage_to__pattern__codebase=codebase2).all()

    progress_monitor = CLIProgressMonitor(min_step=1.0)
    recs = pcoverage.compute_coverage_recommendation(coverage_diffs,
            progress_monitor)
    pcoverage.compute_super_recommendations(recs,
            progress_monitor)


def show_addition_reco(pname, bname, release1, release2, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    super_recs = SuperAddRecommendation.objects.\
            filter(resource_object_id=resource_pk).\
            filter(source=source).\
            filter(codebase_from=codebase1).\
            filter(codebase_to=codebase2).all()

    pcoverage.report_super(super_recs)


def compute_remove_reco(pname, bname, release1, release2, source, resource_pk,
        keep_all=True):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    recs = []
    query = codebase1.code_elements.all()
    progress_monitor = CLIProgressMonitor(min_step=1.0)
    progress_monitor.start('Processing code elements', query.count())

    for code_element in query:
        if not code_element_linked(code_element, source, resource_pk):
            progress_monitor.work('Skipped code element', 1)
            continue

        (equivalent, exact) = find_equivalent(code_element, codebase2)
        rec = RemoveRecommendation(code_element_from=code_element,
                code_element_to=equivalent, codebase_from=codebase1,
                codebase_to=codebase2,
                resource_content_type=get_content_type(source),
                resource_object_id=resource_pk,
                source=source)

        if equivalent is None:
            rec.save()
            recs.append(rec)
        elif not exact:
            deprecated = find_deprecated(equivalent)
            if deprecated:
                rec.deprecated_element = deprecated
                # If not keep all, ensure that the element was not already
                # deprecated
                if keep_all or not find_deprecated(code_element):
                    rec.save()
                    recs.append(rec)
            else:
                rec.save()
                recs.append(rec)
        else:
            deprecated = find_deprecated(equivalent)
            # If not keep all, ensure that the element was not already
            # deprecated
            if deprecated and (keep_all or not find_deprecated(code_element)):
                rec.deprecated_element = deprecated
                rec.save()
                recs.append(rec)

        progress_monitor.work('Processed code element', 1)

    progress_monitor.done()

    report_remove_recs(recs)


def clear_remove_reco(pname, bname, release1, release2, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    query = RemoveRecommendation.objects.filter(codebase_from=codebase1).\
            filter(codebase_to=codebase2).filter(source=source).\
            filter(resource_object_id=resource_pk)

    print('Deleting {0} remove recommendations'.format(query.count()))
    query.all().delete()


def report_remove_reco(pname, bname, release1, release2, source, resource_pk):
    prelease1 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release1)[0]
    codebase1 = CodeBase.objects.filter(project_release=prelease1).\
            filter(name=bname)[0]
    prelease2 = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release2)[0]
    codebase2 = CodeBase.objects.filter(project_release=prelease2).\
            filter(name=bname)[0]

    query = RemoveRecommendation.objects.filter(codebase_from=codebase1).\
            filter(codebase_to=codebase2).filter(source=source).\
            filter(resource_object_id=resource_pk)
    report_remove_recs(query.all())


### Internal Functions ###

def report_remove_recs(recs):
    print('\nREMOVE RECOMMENDATIONS\n')
    print('COUNT: {0}\n'.format(len(recs)))

    for rec in recs:
        print(rec.human_string())
        links = get_code_element_links(rec.code_element_from, rec.source,
                rec.resource_object_id)
        for link in links.all():
            print('  {0} in {1}/{2}'.format(link.code_reference.content,
                link.code_reference.local_context,
                link.code_reference.global_context))


def code_element_linked(code_element, source, resource_pk):
    return get_code_element_links(code_element, source, resource_pk).exists()


def get_code_element_links(code_element, source, resource_pk):
    return  CodeElementLink.objects.filter(code_element=code_element).\
            filter(code_reference__source=source).\
            filter(code_reference__resource_object_id=resource_pk).\
            filter(index=0)


def find_equivalent(code_element, codebase):
    count = 0
    return_code_element = None
    exact = False
    human_string = code_element.human_string()
    code_elements = codebase.code_elements.filter(fqn=code_element.fqn).\
            filter(kind=code_element.kind).all()

    for temp in code_elements:
        count += 1
        if human_string == temp.human_string():
            return_code_element = temp
            exact = True
            break

    if code_element is None and count > 0:
        return_code_element = code_elements[0]

    return (return_code_element, exact)


def find_deprecated(code_element):
    if code_element is None:
        return None
    elif code_element.deprecated:
        return code_element
    else:
        containers = list(code_element.containers.all())
        if len(containers) > 0:
            return find_deprecated(containers[0])
        else:
            return None


def index_high_level_links(result, section_type_id, msg_type_id):
    msgs_index = {}
    sections_index = {}
    code_index = {}
    msg_type = ContentType.objects.get(pk=msg_type_id)
    section_type = ContentType.objects.get(pk=section_type_id)

    for line in result:
        msg_id = int(line['msg_id'])
        section_id = int(line['section_id'])
        code_id = int(line['code_id'])

        if msg_id in msgs_index:
            message = msgs_index[msg_id][0]
        else:
            message = msg_type.get_object_for_this_type(pk=msg_id)
            msgs_index[msg_id] = (message, {})
        if section_id in sections_index:
            section = sections_index[section_id][0]
        else:
            section = section_type.get_object_for_this_type(pk=section_id)
            sections_index[section_id] = (section, {})
        if code_id in code_index:
            code = code_index[code_id][0]
        else:
            code = CodeElement.objects.get(pk=code_id)
            code_index[code_id] = (code, CodeLink(code))

        msg_links = msgs_index[msg_id][1]
        if section.pk not in msg_links:
            msg_link = HighLink(message, section)
            msg_links[section.pk] = msg_link
        msg_links[section.pk].codes.append(code)

        section_links = sections_index[section_id][1]
        if message.pk not in section_links:
            section_link = HighLink(message, section)
            section_links[message.pk] = section_link
        section_links[message.pk].codes.append(code)

        code_index[code_id][1].pairs.append((section, message))

    return (msgs_index, sections_index, code_index)


def report_msg_high_level(msgs_index):
    sum_sections = 0
    size = len(msgs_index)
    print('\nMESSAGE INDEX\n')
    for msg_id in msgs_index:
        (message, links) = msgs_index[msg_id]
        print('\n  Message {0}'.format(message.pk))
        print('    {0}: {1} ({2})'.format(message.title.encode('ascii',
            errors='ignore'), message.index,
            message.author.__unicode__().encode('ascii', errors='ignore')))
        print('    url: {0}'.format(message.url))
        print('\n    SECTIONS:')
        for section_id in links:
            sum_sections += 1
            link = links[section_id]
            print('    {0} ({1})'.format(link.section.title,
                link.section.page.title)) 
            for code in link.codes:
                print('      {0}'.format(code.fqn))

    if size > 0:
        average = float(sum_sections) / size
    else:
        average = 0.0

    print('\n  MESSAGE INDEX SUMMARY')
    print('    Number of messages: {0}'.format(size))
    print('    Average sections per message: {0}'.format(average))


def report_section_high_level(sections_index):
    sum_msgs = 0
    size = len(sections_index)
    print('\nSECTION INDEX\n')
    for section_id in sections_index:
        (section, links) = sections_index[section_id]
        print('\n  Section {0}'.format(section.pk))
        print('    {0}: ({1}))'.format(section.title, section.page.title))
        print('\n    MESSAGES:')
        for message_id in links:
            sum_msgs += 1
            link = links[message_id]
            print('    {0}: {1} ({2})'.format(link.msg.title.encode('ascii',
                errors='ignore'),
                link.msg.index,
                link.msg.author.__unicode__().encode('ascii', errors='ignore')))
            print('    {0}'.format(link.msg.url))
            for code in link.codes:
                print('      {0}'.format(code.fqn))

    if size > 0:
        average = float(sum_msgs) / size
    else:
        average = 0.0

    print('\n  SECTION INDEX SUMMARY')
    print('    Number of sections: {0}'.format(size))
    print('    Average messages per section: {0}'.format(average))


def report_code_high_level(code_index):
    sum_code = 0
    size = len(code_index)
    print('\nCODE INDEX\n')
    for code_id in code_index:
        (code, link) = code_index[code_id]
        print('\n  Code: {0}'.format(code.fqn))
        print('\n    PAIRS:')
        for pair in link.pairs:
            sum_code += 1
            print('    pair:')
            print('      {0}: ({1})'.format(pair[0].title, pair[0].page.title))
            print('      {0}: {1} ({2})'.format(pair[1].title.encode('ascii',
                errors='ignore'), pair[1].index,
                pair[1].author.__unicode__().encode('ascii', errors='ignore')))

    if size > 0:
        average = float(sum_code) / size
    else:
        average = 0.0
    
    print('\n  CODE INDEX SUMMARY')
    print('    Number of code elements: {0}'.format(size))
    print('    Average pairs per code: {0}'.format(average))

from __future__ import unicode_literals
from docutil.progress_monitor import CLIProgressMonitor
from docutil.commands_util import get_content_type
from project.models import ProjectRelease
from codebase.models import CodeBase, CodeElementLink
from recommender.models import CodeElementFamily, CoverageDiff,\
    SuperAddRecommendation, RemoveRecommendation
import recommender.parser.family_coverage as fcoverage

def compute_families(pname, bname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    code_elements = codebase.code_elements.all()

    progress_monitor = CLIProgressMonitor(min_step=1.0)

    dfamilies = fcoverage.compute_declaration_family(code_elements, True,
            progress_monitor)
    (hfamilies1, hfamiliesd) = fcoverage.\
            compute_hierarchy_family(code_elements, True, progress_monitor)

    fcoverage.compute_no_abstract_family(dfamilies, progress_monitor)
    fcoverage.compute_no_abstract_family(hfamilies1, progress_monitor)
    fcoverage.compute_no_abstract_family(hfamiliesd, progress_monitor)

    fcoverage.compute_token_family_second(dfamilies, progress_monitor)

    fcoverage.compute_token_family(code_elements, True, progress_monitor)


def clear_families(pname, bname, release):
    prelease = ProjectRelease.objects.filter(project__dir_name=pname).\
            filter(release=release)[0]
    codebase = CodeBase.objects.filter(project_release=prelease).\
            filter(name=bname)[0]
    CodeElementFamily.objects.filter(codebase=codebase).delete()


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

    fcoverage.compare_coverage(codebase1, codebase2, source, resource_pk,
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
            filter(coverage_from__family__codebase=codebase1).\
            filter(coverage_to__resource_object_id=resource_pk).\
            filter(coverage_to__source=source).\
            filter(coverage_to__family__codebase=codebase2).all()

    progress_monitor = CLIProgressMonitor(min_step=1.0)
    recs = fcoverage.compute_coverage_recommendation(coverage_diffs,
            progress_monitor)
    fcoverage.compute_super_recommendations(recs,
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

    fcoverage.report_super(super_recs)


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
            filter(code_reference__resource_object_id=resource_pk)


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

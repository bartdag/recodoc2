from __future__ import unicode_literals
from docutil.progress_monitor import CLIProgressMonitor
from project.models import ProjectRelease
from codebase.models import CodeBase
from recommender.models import CodeElementFamily, CoverageDiff,\
    SuperAddRecommendation
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

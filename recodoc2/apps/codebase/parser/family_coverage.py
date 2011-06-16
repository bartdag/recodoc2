from __future__ import unicode_literals
import codebase.models as cmodel
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import size

# TODO
# 1- Declaration/Hierarchy families should be based on kind too
# So key of dict is container.pk dash kind of element.pk
# 2- Hierarchy is only direct.
# What happen if we compute indirect hierarchy, like level-2?
# 3- please add __unicode__ and plural (not sure how to do this!)

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
        for container in code_element.containers.all():
            pk = container.pk
            if pk not in families:
                families[pk] = create_family(container, cmodel.DECLARATION,
                        first_criterion)
            families[pk].members.add(code_element)
        
        progress_monitor.work('Code Element processed', 1)
    
    progress_monitor.done()
    
    return families


def compute_hierarchy_family(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    families = {}

    progress_monitor.start('Comp. Hierarchy Families', size(code_elements))
    
    for code_element in code_elements:
        for container in code_element.parents.all():
            pk = container.pk
            if pk not in families:
                families[pk] = create_family(container, cmodel.HIERARCHY,
                        first_criterion)
            families[pk].members.add(code_element)

        progress_monitor.work('Code Element processed', 1)
    
    progress_monitor.done()

    return families


def compute_token_family_second(families,
        progress_monitor=NullProgressMonitor()):
    pass


def compute_token_family(code_elements, first_criterion=True,
        progress_monitor=NullProgressMonitor()):
    pass


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

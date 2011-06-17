from __future__ import unicode_literals
import codebase.models as cmodel
import codebase.linker.context as ctx
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import size

# TODO
# 1- Declaration/Hierarchy families should be based on kind too
# So key of dict is container.pk dash kind of element.pk
# 2- Hierarchy is only direct.
# What happen if we compute indirect hierarchy, like level-2?

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
        ancestors = {ancestor.pk : ancestor for ancestor in ancestors_list}


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

from __future__ import unicode_literals

from codebase.models import CodeBaseDiff, CodeElement


class JavaDiffer(object):

    def diff(self, fcodebase, tcodebase):
        cdiff = CodeBaseDiff()
        cdiff.codebase_from = fcodebase
        cdiff.codebase_to = tcodebase
        cdiff.save()
        fpackages = CodeElement.objects.filter(codebase=fcodebase,
                kind__kind='package')
        tpackages = CodeElement.objects.filter(codebase=tcodebase,
                kind__kind='package')

        self._diff_count(cdiff)
        self._diff_packages(cdiff, fpackages, tpackages)

        cdiff.save()
        return cdiff

    def _diff_count(self, cdiff):
        cdiff.packages_size_from = \
            cdiff.codebase_from.code_elements.filter(kind__kind='package')\
            .count()
        cdiff.packages_size_to = \
            cdiff.codebase_to.code_elements.filter(kind__kind='package')\
            .count()

        cdiff.types_size_from = \
            cdiff.codebase_from.code_elements.filter(kind__is_type=True)\
            .count()
        cdiff.types_size_to = \
            cdiff.codebase_to.code_elements.filter(kind__is_type=True).count()

        cdiff.methods_size_from = \
            cdiff.codebase_from.code_elements.filter(kind__kind='method')\
            .count()
        cdiff.methods_size_to = \
            cdiff.codebase_to.code_elements.filter(kind__kind='method').count()

        cdiff.fields_size_from = \
            cdiff.codebase_from.code_elements.filter(kind__kind='field')\
            .count()
        cdiff.fields_size_to = \
            cdiff.codebase_to.code_elements.filter(kind__kind='field').count()

        cdiff.enum_values_size_from = \
            cdiff.codebase_from.code_elements.filter(
                    kind__kind='enumeration value').count()
        cdiff.enum_values_size_to = \
            cdiff.codebase_to.code_elements.filter(
                    kind__kind='enumeration value').count()

        cdiff.ann_fields_size_from = \
            cdiff.codebase_from.code_elements.filter(
                    kind__kind='annotation field').count()
        cdiff.ann_fields_size_to = \
            cdiff.codebase_to.code_elements.filter(
                    kind__kind='annotation field').count()

        cdiff.save()

    def _diff_packages(self, cdiff, fpackages, tpackages):
        from_fqns = dict((fpackage.fqn, fpackage) for fpackage in
                fpackages.all())
        to_fqns = dict((tpackage.fqn, tpackage) for tpackage in
                tpackages.all())
        from_types = []
        to_types = []

        for from_fqn in from_fqns:
            if from_fqn not in to_fqns:
                from_package = from_fqns[from_fqn]
                cdiff.removed_packages.add(from_package)
            else:
                from_package = from_fqns[from_fqn]
                from_types.extend(from_package.containees.
                        filter(kind__is_type=True).all())

                to_package = to_fqns[from_fqn]
                to_types.extend(to_package.containees.
                        filter(kind__is_type=True).all())

        for to_fqn in to_fqns:
            if to_fqn not in from_fqns:
                to_package = to_fqns[to_fqn]
                cdiff.added_packages.add(to_fqns[to_fqn])

        self._diff_types(cdiff, from_types, to_types)

    def _diff_types(self, cdiff, ftypes, ttypes):
        from_fqns = dict((ftype.fqn, ftype) for ftype in
                ftypes)
        to_fqns = dict((ttype.fqn, ttype) for ttype in
                ttypes)
        types = []

        for from_fqn in from_fqns:
            if from_fqn not in to_fqns:
                from_type = from_fqns[from_fqn]
                cdiff.removed_types.add(from_type)
            else:
                from_type = from_fqns[from_fqn]
                to_type = to_fqns[from_fqn]
                types.append((from_type, to_type))

        for to_fqn in to_fqns:
            if to_fqn not in from_fqns:
                to_type = to_fqns[to_fqn]
                cdiff.added_types.add(to_type)

        for (ftype, ttype) in types:
            self._diff_type(cdiff, ftype, ttype)

    def _diff_type(self, cdiff, ftype, ttype):
        from_fqns = dict((method.human_string(), method) for method in
                ftype.containees.filter(kind__kind='method').all())
        to_fqns = dict((method.human_string(), method) for method in
                ttype.containees.filter(kind__kind='method').all())
        self._diff_type_members(cdiff, from_fqns, to_fqns,
                cdiff.removed_methods, cdiff.added_methods)

        from_fqns = dict((method.human_string(), method) for method in
                ftype.containees.filter(kind__kind='field').all())
        to_fqns = dict((method.human_string(), method) for method in
                ttype.containees.filter(kind__kind='field').all())
        self._diff_type_members(cdiff, from_fqns, to_fqns,
                cdiff.removed_fields, cdiff.added_fields)

        from_fqns = dict((method.human_string(), method) for method in
                ftype.containees.filter(kind__kind='enumeration value').all())
        to_fqns = dict((method.human_string(), method) for method in
                ttype.containees.filter(kind__kind='enumeration value').all())
        self._diff_type_members(cdiff, from_fqns, to_fqns,
                cdiff.removed_enum_values, cdiff.added_enum_values)

        from_fqns = dict((method.human_string(), method) for method in
                ftype.containees.filter(kind__kind='annotation field').all())
        to_fqns = dict((method.human_string(), method) for method in
                ttype.containees.filter(kind__kind='annotation field').all())
        self._diff_type_members(cdiff, from_fqns, to_fqns,
                cdiff.removed_ann_fields, cdiff.added_ann_fields)

    def _diff_type_members(self, cdiff, from_fqns, to_fqns, removed, added):
        for from_fqn in from_fqns:
            if from_fqn not in to_fqns:
                from_type = from_fqns[from_fqn]
                removed.add(from_type)

        for to_fqn in to_fqns:
            if to_fqn not in from_fqns:
                to_type = to_fqns[to_fqn]
                added.add(to_type)

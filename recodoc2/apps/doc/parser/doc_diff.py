from __future__ import unicode_literals
from difflib import SequenceMatcher
from doc.models import SectionMatcher, DocDiff, Section, PageMatcher,\
        SectionChanger, LinkChange


ABS_THRESHOLD = 2.0
RELATIVE_THRESHOLD = 1.0
RATIO_THRESHOLD = 0.85
DEFAULT_DISTANCES = ((0.90, 0.75), (0.80, 0.50), (0.70, 0.25))


def get_null_matches(from_elem, to_elems, factor):
    mr = MatcherResult(from_elem=from_elem, factor=factor)
    mr.to_elems = {to_elem.pk: [to_elem, 0.0] for to_elem in to_elems}
    return mr


def get_one_match(from_elem, to_elems, factor, to_elem, confidence):
    mr = get_null_matches(from_elem, to_elems, factor)
    mr.to_elems[to_elem.pk] = [to_elem, confidence]
    return mr


def get_confidence_str_distance(text_from, text_to, distances):
    match_ratio = SequenceMatcher(None, text_from, text_to).ratio()
    conf = 0.0
    for (threshold, confidence) in distances:
        if match_ratio >= threshold:
            conf = confidence + (match_ratio - threshold)
            break
    return conf


def sort_match_results(match_results):
    matches = {}
    for result in match_results:
        for to_pk in result.to_elems:
            if to_pk not in matches:
                matches[to_pk] = [result.to_elems[to_pk][0], 0.0]
            matches[to_pk][1] += result.to_elems[to_pk][1] * result.factor
    sorted_matches = sorted(matches.values(), key=lambda l: l[1], reverse=True)

    return sorted_matches


def has_best_match(sorted_results):
    if len(sorted_results) <= 1:
        return True

    return sorted_results[0][1] > ABS_THRESHOLD and \
        (sorted_results[0][1] - sorted_results[1][1]) > RELATIVE_THRESHOLD


def get_best_match(match_results):
    sorted_results = sort_match_results(match_results)
    if has_best_match(sorted_results):
        return sorted_results[0]
    else:
        return None


class MatcherResult(object):

    def __init__(self, from_elem=None, factor=None):
        self.from_elem = from_elem
        self.factor = factor
        self.to_elems = {}


class SectionNumberMatcher(object):

    factor = 10.0

    def match(self, section_from, section_tos):
        fnumber = section_from.number.strip()
        ftitle = section_from.title.strip()
        mresult = get_null_matches(section_from, section_tos, self.factor)

        if fnumber == '':
            return mresult

        for section_to in section_tos:
            ttitle = section_to.title.strip()
            tnumber = section_to.number.strip()
            if fnumber == tnumber and ftitle == ttitle:
                mresult.to_elems[section_to.pk][1] = 1.0
                break
            elif fnumber == tnumber:
                conf = get_confidence_str_distance(ftitle, ttitle,
                        DEFAULT_DISTANCES)
                mresult.to_elems[section_to.pk][1] = conf
                break

        return mresult


class TitleMatcher(object):

    factor = 5.0

    def match(self, from_elem, to_elems):
        ftitle = from_elem.title.strip()
        mresult = MatcherResult(from_elem, self.factor)
        for to_elem in to_elems:
            ttitle = to_elem.title.strip()
            if ftitle == to_elem.title.strip():
                mresult.to_elems[to_elem.pk] = [to_elem, 1.0]
            else:
                conf = get_confidence_str_distance(ftitle, ttitle,
                        DEFAULT_DISTANCES)
                mresult.to_elems[to_elem.pk] = [to_elem, conf]
        return mresult


class ChildrenMatcher(object):

    factor = 3.0

    def _children(self, elem):
        children = []
        try:
            children = list(elem.sections.all())
        except Exception:
            try:
                children = list(elem.children.all())
            except Exception:
                children = []
        return children

    def _max_ratio(self, title, children_names):
        max_ratio = 0.0
        for child_name in children_names:
            ratio = SequenceMatcher(None, title, child_name).ratio()
            if ratio > max_ratio:
                max_ratio = ratio

        return max_ratio

    def match(self, from_elem, to_elems):
        children = self._children(from_elem)
        children_size = len(children)
        mresult = get_null_matches(from_elem, to_elems, self.factor)
        
        if children_size == 0:
            return mresult

        for to_elem in to_elems:
            to_children = self._children(to_elem)
            children_names = [child.title.strip() for child in to_children]
            matches = 0.0
            for child in children:
                ratio = self._max_ratio(child.title.strip(), children_names)
                if ratio >= RATIO_THRESHOLD:
                    matches += RATIO_THRESHOLD + (ratio - RATIO_THRESHOLD)

            conf = matches / children_size
            mresult.to_elems[to_elem.pk][1] = conf

        return mresult
        

class SectionParentMatcher(object):

    factor = 2.0

    def match(self, from_elem, to_elems):
        mresult = get_null_matches(from_elem, to_elems, self.factor)

        if from_elem.parent is None:
            return mresult

        ptitle = from_elem.parent.title.strip()
        pnumber = from_elem.parent.number.strip()

        for to_elem in to_elems:
            conf = 0.0
            parent = to_elem.parent
            if parent is None:
                continue

            pttitle = parent.title.strip()
            ptnumber = parent.number.strip()
            if pnumber != '' and pnumber == ptnumber:
                conf += 0.5

            ratio = SequenceMatcher(None, ptitle, pttitle).ratio()
            if ratio >= RATIO_THRESHOLD:
                new_conf = RATIO_THRESHOLD + (ratio - RATIO_THRESHOLD)
                if pnumber == '':
                    conf += new_conf
                else:
                    conf += new_conf/2.0
            mresult.to_elems[to_elem.pk][1] = conf

        return mresult


class SectionPageMatcher(object):

    factor = 1.0

    def match(self, from_elem, to_elems):
        mresult = get_null_matches(from_elem, to_elems, self.factor)
        ptitle = from_elem.page.title.strip()
        for to_elem in to_elems:
            pttitle = to_elem.page.title.strip()
            ratio = SequenceMatcher(None, ptitle, pttitle).ratio()
            if ratio >= RATIO_THRESHOLD:
                conf = RATIO_THRESHOLD + (ratio - RATIO_THRESHOLD)
                mresult.to_elems[to_elem.pk] = [to_elem, conf]
        return mresult


class DocDiffer(object):

    def diff_docs(self, document_from, document_to):
        ddiff = DocDiff()
        ddiff.document_from = document_from
        ddiff.document_to = document_to
        ddiff.pages_size_from = document_from.pages.count()
        ddiff.pages_size_to = document_to.pages.count()

        ddiff.sections_size_from =\
            Section.objects.filter(page__document=document_from).count()
        ddiff.sections_size_to =\
            Section.objects.filter(page__document=document_to).count()
        ddiff.save()

        self.match_pages(ddiff)

        self.match_sections(ddiff)

        self.compute_changes(ddiff)
        
        return ddiff

    def match_pages(self, ddiff):
        page_tos = list(ddiff.document_to.pages.all())
        matched_tos = set()
        for page_from in ddiff.document_from.pages.all():
            best_match = self._match_page(page_from, page_tos)
            if best_match is not None:
                (page_to, confidence) = best_match
                p_matcher = PageMatcher(
                        page_from=page_from,
                        page_to=page_to,
                        confidence=confidence,
                        diff=ddiff)
                p_matcher.save()
                matched_tos.add(page_to.pk)
            else:
                ddiff.removed_pages.add(page_from)

        for page_to in page_tos:
            if page_to.pk not in matched_tos:
                ddiff.added_pages.add(page_to)

        print('Finished matching pages')

    def match_sections(self, ddiff):
        section_froms = list(Section.objects
                .filter(page__document=ddiff.document_from).all())
        section_tos = list(Section.objects
                .filter(page__document=ddiff.document_to).all())
        matched_tos = set()
        for section_from in section_froms:
            best_match = self._match_section(section_from, section_tos)
            if best_match is not None:
                (section_to, confidence) = best_match
                s_matcher = SectionMatcher(
                        section_from=section_from,
                        section_to=section_to,
                        confidence=confidence,
                        diff=ddiff)
                s_matcher.save()
                matched_tos.add(section_to.pk)
            else:
                ddiff.removed_sections.add(section_from)
            print('Matched section {0}'.format(section_from.title))

        for section_to in section_tos:
            if section_to.pk not in matched_tos:
                ddiff.added_sections.add(section_to)
                print('Matched section to')

        print('Finished matching sections')

    def compute_changes(self, ddiff):
        for section_matcher in ddiff.section_matches.all():
            section_from = section_matcher.section_from
            section_to = section_matcher.section_to
            words_from = section_from.word_count
            words_to = section_to.word_count

            if words_from > 0:
                change_words = (float(words_to - words_from) /
                        float(words_from)) * 100.0
            else:
                change_words = words_to * 100.0

            if words_from != words_to:
                change = SectionChanger(section_from=section_from,
                        section_to=section_to,
                        words_from=words_from,
                        words_to=words_to,
                        change=change_words,
                        diff=ddiff)
                change.save()

        print('Finished computing changes')

    def _match_page(self, page_from, page_tos):
        match_results = []
        match_results.append(TitleMatcher().match(page_from, page_tos))
        match_results.append(ChildrenMatcher().match(page_from, page_tos))
        best_match = get_best_match(match_results)
        return best_match

    def _match_section(self, section_from, section_tos):
        match_results = []
        match_results.append(
                SectionNumberMatcher().match(section_from, section_tos))
        match_results.append(
                TitleMatcher().match(section_from, section_tos))
        match_results.append(
                ChildrenMatcher().match(section_from, section_tos))
        match_results.append(
                SectionParentMatcher().match(section_from, section_tos))
        match_results.append(
                SectionPageMatcher().match(section_from, section_tos))
        best_match = get_best_match(match_results)
        return best_match


class DocLinkerDiffer(object):
    
    def __init__(self, docdiff):
        self.docdiff = docdiff

    def diff_links(self):
        added_links = []
        removed_links = []
        processed_sections = set()

        sections_from = Section.objects.\
                filter(page__document=self.docdiff.document_from).all()
        sections_to = Section.objects.\
                filter(page__document=self.docdiff.document_to).all()

        self._process_sections_from(added_links, removed_links,
                processed_sections, sections_from)

        self._process_sections_to(added_links, removed_links,
                processed_sections, sections_to)
        return (added_links, removed_links)

    def _process_sections_from(self, added_links, removed_links,
            processed_sections, sections_from):
        for section_from in sections_from:
            try:
                matcher = section_from.match_froms.get(diff=self.docdiff)
                section_to = matcher.section_to
                links_from = self._get_links(section_from)
                links_to = self._get_links(section_to)
                self._diff_links(links_from, links_to, added_links,
                        removed_links)
                processed_sections.add(section_to.pk)
            except Exception:
                self._add_removed_links(section_from, removed_links)

    def _process_sections_to(self, added_links, removed_links,
            processed_sections, sections_to):
        for section_to in sections_to:
            if section_to.pk not in processed_sections:
                self._add_added_links(section_to, added_links)

    def _get_links(self, section):
        links = []
        for single_ref in section.code_references.all():
            link = self._get_link(single_ref,
                    single_ref.project_release)
            if link is not None:
                links.append(link)
        return links

    def _diff_links(self, links_from, links_to, added_links, removed_links):
        for link_from in links_from:
            link_to = self._pop_link(link_from, links_to)
            # This means the link was removed!
            if link_to is None:
                link_change = LinkChange(diff=self.docdiff,
                        link_from=link_from, from_matched_section=True)
                link_change.save()
                removed_links.append(link_change)

        # Remaining links were added!
        for link_to in links_to:
            link_change = LinkChange(diff=self.docdiff,
                    link_to=link_to, from_matched_section=True)
            link_change.save()
            added_links.append(link_change)


    def _pop_link(self, link_to_find, links):
        index = -1
        link = None
        human_string = link_to_find.code_element.human_string()
        is_snippet = link_to_find.code_reference.snippet is not None
        
        for i, temp_link in enumerate(links):
            temp_human = temp_link.code_element.human_string()     
            temp_snippet = temp_link.code_reference.snippet is not None
            if human_string == temp_human and is_snippet == temp_snippet:
                index = i
                link = temp_link
                break

        if index > -1:
            del links[index]

        return link

    def _add_removed_links(self, section, removed_links):
        for link in self._get_links(section):
            if link is None:
                continue
            else:
                link_change = LinkChange(
                        diff=self.docdiff,
                        link_from=link)
                link_change.save()
                removed_links.append(link_change)

    def _add_added_links(self, section, added_links):
        for link in self._get_links(section):
            if link is None:
                continue
            else:
                link_change = LinkChange(
                        diff=self.docdiff,
                        link_to=link)
                link_change.save()
                added_links.append(link_change)

    def _get_link(self, code_reference, project_release):
        link = None
        try:
            release_links = code_reference.release_links.\
                get(project_release=project_release)
            link = release_links.first_link
        except Exception:
            pass
        return link

import os
import pickle
import re
import urllib
from typing import Optional

from my_wiktionary_parser import MyWiktionaryParser as WiktionaryParser
from util import language_to_code
from pickling_base import PicklingBaseClass


def should_skip_lemma(lemma: str):
    # most_frequent_lemmas = ['sobre', 'eria', 'illo', 'miento', 'mente', 'ería', 'mente', 'illo', 'eria']
    most_frequent_lemmas = []
    lemma = lemma.strip('-')
    return (len(lemma) > 3) or (lemma in most_frequent_lemmas)


class WiktionaryCache(PicklingBaseClass):
    lemma_parts_re = r"(From )?(([a-zA-Z0-9À-ž]+-?( \(\“.+\”\))?)( \+‎ -?[a-zA-Z0-9À-ž]*-?)+)(;.*)?"
    from_or_see_re = r"(Diminutive of|From|See|From the [a-zA-Z0-9À-ž]+) ([a-zA-Z0-9À-ž]+)( *\(.*\))*.?$"
    past_participle_re = r"(Past participle|Clipping|From the participle) of ([a-zA-Z0-9À-ž]+)"
    origin_of_re = r'.* of ([a-zA-Z0-9À-ž]+)( combined with.*)?[\.:]?$'
    compound_of_re = r'Compound of the [a-zA-Z0-9À-ž]+ ([a-zA-Z0-9À-ž]+) .*'

    def __init__(self, language):
        self.lang_code = language_to_code(language)
        self.parser = WiktionaryParser()
        self.parser.set_default_language(language)
        self.parser.exclude_relation("related terms")
        self.definitions = {}
        self.sources = {}
        self.dirty_count = 0
        super().__init__(language)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle baz
        del state["parser"]
        del state['dirty_count']
        return state

    def __setstate__(self, state):
        self.sources = {}  # in case we don't have it yet
        self.__dict__.update(state)
        # Add baz back since it doesn't exist in the pickle
        self.parser = WiktionaryParser()
        self.parser.set_default_language(self.language)
        self.parser.exclude_relation("related terms")
        self.dirty_count = 0

    def bump_dirty(self):
        self.dirty_count += 1
        if self.dirty_count >= 20:
            self.save()
            print("-- save --")
            self.dirty_count = 0

    def define_full_2(self, max_defs: int, base: str, lemma: Optional[str]) -> str:
        definitions = self.parser.fetch_recursive(max_defs, base, lemma, self.language, self)
        lines = [WiktionaryCache.to_html(x['definition'], x['wiki_word']['word'], x['wiki_word']['language']) for x in definitions]
        return '\n'.join(lines)

    def define_full(self, max_defs: int, base: str, lemma: Optional[str], source: str) -> str:
        defs = self._define_full({}, max_defs, base, lemma, source)
        defs = filter(lambda x: len(x.strip()) > 0, defs)
        return "\n".join(defs)

    def define_full_list(self, max_defs: int, base: str, lemma: Optional[str], source: str) -> [str]:
        return self._define_full({}, max_defs, base, lemma, source)

    def _define_full(self, already_defined: dict, max_defs: int, base: str, lemma: Optional[str], source: str) -> [str]:
        debug = False
        if debug:
            print(f"_define_full: called with:({[already_defined, max_defs, base, lemma, source]})")
        base = base.lower()
        parts = base.split(' ')
        if len(parts) > 1:
            parts.sort(key=lambda x: -len(x))
            base = parts[0]
        if base in already_defined:
            return []

        if len(list(already_defined.keys())) >= max_defs:
            return []

        to_define = base
        all_defs = []
        all_defs.append(self.define(to_define, source))
        already_defined[to_define] = True

        child_lemmas = self.get_lemmas(to_define)

        if (lemma is not None) and (lemma != base):
            if debug:
                print("_define_full: add lemma ", lemma)
            to_define = lemma.lower()
            all_defs.append(self.define(to_define, source))
            if debug:
                print(f"_define_full: define({to_define}, {source}) = {all_defs[-1]}")
            already_defined[to_define] = True
            child_lemmas += self.get_lemmas(to_define)

        if debug:
            print("_define_full: child_lemmas = ", child_lemmas)

        for child_word in child_lemmas:
            if should_skip_lemma(child_word):
                if debug:
                    print("_define_full: recurse:", child_word, already_defined)
                all_defs += self._define_full(already_defined, max_defs, child_word, None, "definition " + base)
            else:
                if debug:
                    print("_define_full: skip common lemma:", child_word)

        return all_defs

    @staticmethod
    def load(language: str) -> 'WiktionaryCache':
        return PicklingBaseClass.s_load(language, WiktionaryCache)


    """
[{'definitions': [{
                   'partOfSpeech': 'noun',
                   'text': [
                        'mano\xa0f (plural mani or (archaic or dialectal) invariable)',
                        '(anatomy) hand',
                        'band, company (Boccaccio; v. manus)',
                        'round']}],
  'etymology': 'From Latin manus (whence also English manual, etc.), from '
               'Proto-Italic *manus, perhaps from Proto-Indo-European *méh₂-r̥ '
               '~ *mh₂-én-, derived from Proto-Indo-European *(s)meh₂- (“to '
               'beckon”), or perhaps from a Proto-Indo-European *mon-u- (see '
               'the Proto-Italic entry).\n',
  'pronunciations': {'audio': [],
                     'text': ['IPA: /ˈma.no/',
                              'Rhymes: -ano',
                              'Hyphenation: mà‧no']}}]
    """

    @staticmethod
    def to_html(data, word, language: str = '') -> str:
        d_word = urllib.parse.unquote(word)

        output = ""
        for output_data in data:
            defs = output_data['definitions']  # list of definitions
            for i in range(0, len(defs)):
                def_data = defs[i]
                if 'partOfSpeech' in def_data:
                    output += f"<h4>{def_data['partOfSpeech']}</h4>"
                else:
                    output += "<h4>definition</h4>"
                if 'text' in def_data:
                    output += "<ul>"
                    for item in def_data['text']:
                        output += f"<li>{item}</li>"
                    output += "</ul>"
            if 'etymology' in output_data:
                if len(f"{output_data['etymology']}") > 0:
                    output += f"\n   <h4>etymology</h4><p>{output_data['etymology']}</p>"
        if len(output) > 0:
            if len(language) > 0:
                language = language + " "
            output = f"<h3>{language}definition of {d_word}</h3>" + output
        return output

    @staticmethod
    def contains_reference_to_other_language(term):
        term = term.lower()
        for lang in ['latin', 'old spanish', 'occitan', 'english', 'arabic', 'galician', 'french', 'japanese',
                     'hokkien', 'portuguese', 'greek', 'gothic', 'taíno', 'catalan', 'italian', 'onomatopoetic',
            'dutch', 'nahuatl']:
            if term.find(lang) > -1:
                return True
        return False  # not found

    def get_lemmas(self, term):
        lemmas = []
        for output_data in self.definitions[term]:
            for def_data in output_data['definitions']:
                if 'text' in def_data:
                    for item in def_data['text']:
                        match = re.match(self.origin_of_re, item)
                        if match is not None:
                            lemmas.append(match.group(1))
                        else:
                            match = re.match(self.compound_of_re, item)
                            if match is not None:
                                lemmas.append(match.group(1))

            etym = output_data.get('etymology', '').strip()
            if len(etym) == 0:
                continue

            # first, look for "From abc" or "See xyz" etymologies
            match = re.match(self.from_or_see_re, etym)
            if match is not None:
                lemmas.append(match.group(2))
                continue

            match = re.search(self.past_participle_re, etym)
            if match is not None:
                lemmas.append(match.group(2))
                continue

            match = re.match(self.compound_of_re, etym)
            if match is not None:
                lemmas.append(match.group(1))
                continue


            # next, look for From a- + xyz + -d
            # print("look for match in ", etym)
            match = re.search(self.lemma_parts_re, etym)
            if match is not None:
                parts = match.group(2).split('+\u200e')
                lemmas = lemmas + list(map(lambda x: re.sub(r" \(.*\)", '', x.strip()), parts))
                continue

        # if not WiktionaryCache
        # .contains_reference_to_other_language(etym):
        #     print("NO LEMMA FOUND:", term, etym.lower().find('latin'), etym)
        return lemmas  # nothing found

    # returns an array of definitions. Let's
    def define(self, term: str, source: str) -> str:
        if len(source) > 0:
            key = term.lower()
            if key not in self.sources:
                self.sources[key] = set()
            self.sources[key].add(source.lower())
        if term not in self.definitions:
            print("define", term)
            data = self.parser.fetch(term)
            self.definitions[term] = data
            self.save()

        # import pprint
        # pprint.pprint(self.definitions[term])
        return self.to_html(self.definitions[term], term)


def find_most_common_lemmas(wc: WiktionaryCache):
    lemma_count = {}
    for k, v in wc.definitions.items():
        lemmas = wc.get_lemmas(k)
        for lemma in lemmas:
            lemma_count[lemma] = lemma_count.get(lemma, 0) + 1
    all_lemmas = [(x, y) for x, y in lemma_count.items()]
    all_lemmas.sort(key=lambda x: x[1])
    for l in all_lemmas:
        if should_skip_lemma(l[0]):
            print(l)

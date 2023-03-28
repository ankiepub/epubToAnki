"""
This is a modified version of the WiktionaryParser on GitHub at https://github.com/Suyash458/WiktionaryParser

Modifications were made to:
 1. parse and return lemma information as well as
 2. return derived terms and descendants
 3. cache html responses in a sqlite file at Caches/wiktionary_cache. Cache entries expire after 100 days.


MIT License

Copyright (c) 2019 Suyash Behera <Suyash.behera458@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import re, requests
from utils import WordData, Definition, RelatedWord
from bs4 import BeautifulSoup
from itertools import zip_longest
from copy import copy
from string import digits
import re
from datetime import timedelta
from requests_cache import CachedSession
from typing import TypedDict, List, Optional, Union, Tuple


PARTS_OF_SPEECH = [
    "noun", "verb", "adjective", "adverb", "determiner",
    "article", "preposition", "conjunction", "proper noun",
    "letter", "character", "phrase", "proverb", "idiom",
    "symbol", "syllable", "numeral", "initialism", "interjection",
    "definitions", "pronoun", "participle", "derived terms", "descendants"
]

RELATIONS = [
    "synonyms", "antonyms", "hypernyms", "hyponyms",
    "meronyms", "holonyms", "troponyms", "related terms",
    "coordinate terms",
]


class WikiWord(TypedDict):
    word: str
    language: str


class LemmaResults(TypedDict):
    type: str
    lemma: str
    parts: List[Union[str, List]]


def wiki_words_equals(first: 'WikiWord', other: 'WikiWord') -> bool:
    return (first['word'] == other['word']) and (first['language'].lower() == other['language'].lower())


class WikiDefinition(TypedDict):
    wiki_word: WikiWord
    definition: List


class WikiResults(TypedDict):
    word_data: List
    links: List[WikiWord]


class MyWiktionaryParser(object):
    def __init__(self):
        self.url = "https://en.wiktionary.org/wiki/{}?printable=yes"
        self.soup = None
        self.session = requests.Session()
        self.session = CachedSession(
            'wiktionary_cache',
            use_cache_dir=True,                # Save files in the default user cache dir
            cache_control=False,                # Use Cache-Control headers for expiration, if available
            expire_after=timedelta(days=100),    # Otherwise expire responses after one day
            allowable_methods=['GET', 'POST'], # Cache POST requests to avoid sending the same data twice
            allowable_codes=[200, 400],        # Cache 400 responses as a solemn reminder of your failures
            ignored_parameters=['api_key'],    # Don't match this param or save it in the cache
            match_headers=False,                # Match all request headers
            stale_if_error=True,               # In case of request errors, use stale cache data if possible
        )
        self.session.mount("http://", requests.adapters.HTTPAdapter(max_retries = 2))
        self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries = 2))
        self.language = 'english'
        self.current_word = None
        self.PARTS_OF_SPEECH = copy(PARTS_OF_SPEECH)
        self.RELATIONS = copy(RELATIONS)
        self.INCLUDED_ITEMS = self.RELATIONS + self.PARTS_OF_SPEECH + ['etymology', 'pronunciation']

    def include_part_of_speech(self, part_of_speech):
        part_of_speech = part_of_speech.lower()
        if part_of_speech not in self.PARTS_OF_SPEECH:
            self.PARTS_OF_SPEECH.append(part_of_speech)
            self.INCLUDED_ITEMS.append(part_of_speech)

    def exclude_part_of_speech(self, part_of_speech):
        part_of_speech = part_of_speech.lower()
        self.PARTS_OF_SPEECH.remove(part_of_speech)
        self.INCLUDED_ITEMS.remove(part_of_speech)

    def include_relation(self, relation):
        relation = relation.lower()
        if relation not in self.RELATIONS:
            self.RELATIONS.append(relation)
            self.INCLUDED_ITEMS.append(relation)

    def exclude_relation(self, relation):
        relation = relation.lower()
        self.RELATIONS.remove(relation)
        self.INCLUDED_ITEMS.remove(relation)

    def set_default_language(self, language=None):
        if language is not None:
            self.language = language.lower()

    def get_default_language(self):
        return self.language

    def clean_html(self):
        unwanted_classes = ['sister-wikipedia', 'thumb', 'reference', 'cited-source']
        for tag in self.soup.find_all(True, {'class': unwanted_classes}):
            tag.extract()

    def remove_digits(self, string):
        return string.translate(str.maketrans('', '', digits)).strip()

    def count_digits(self, string):
        return len(list(filter(str.isdigit, string)))

    def get_id_list(self, contents, content_type):
        if content_type == 'etymologies':
            checklist = ['etymology']
        elif content_type == 'pronunciation':
            checklist = ['pronunciation']
        elif content_type == 'definitions':
            checklist = self.PARTS_OF_SPEECH
            if self.language == 'chinese':
                checklist += self.current_word
        elif content_type == 'related':
            checklist = self.RELATIONS
        else:
            return None
        id_list = []
        if len(contents) == 0:
            return [('1', x.title(), x) for x in checklist if self.soup.find('span', {'id': x.title()})]
        for content_tag in contents:
            content_index = content_tag.find_previous().text
            text_to_check = self.remove_digits(content_tag.text).strip().lower()
            if text_to_check in checklist:
                content_id = content_tag.parent['href'].replace('#', '')
                id_list.append((content_index, content_id, text_to_check))
        return id_list

    def get_word_data(self, language):
        contents = self.soup.find_all('span', {'class': 'toctext'})
        word_contents = []
        start_index = None
        for content in contents:
            if content.text.lower() == language:
                start_index = content.find_previous().text + '.'
        if len(contents) != 0 and not start_index:
            return []
        for content in contents:
            index = content.find_previous().text
            content_text = self.remove_digits(content.text.lower())
            if index.startswith(start_index) and content_text in self.INCLUDED_ITEMS:
                word_contents.append(content)
        word_data = {
            'examples': self.parse_examples(word_contents),
            'definitions': self.parse_definitions(word_contents),
            'etymologies': self.parse_etymologies(word_contents),
            'related': self.parse_related_words(word_contents),
            'pronunciations': self.parse_pronunciations(word_contents),
        }
        json_obj_list = self.map_to_object(word_data)
        return json_obj_list

    def parse_pronunciations(self, word_contents):
        pronunciation_id_list = self.get_id_list(word_contents, 'pronunciation')
        pronunciation_list = []
        audio_links = []
        pronunciation_text = []
        pronunciation_div_classes = ['mw-collapsible', 'vsSwitcher']
        for pronunciation_index, pronunciation_id, _ in pronunciation_id_list:
            span_tag = self.soup.find_all('span', {'id': pronunciation_id})[0]
            list_tag = span_tag.parent
            while list_tag.name != 'ul':
                list_tag = list_tag.find_next_sibling()
                if list_tag.name == 'p':
                    pronunciation_text.append(list_tag.text)
                    break
                try:
                    if list_tag.name == 'div' and any(_ in pronunciation_div_classes for _ in list_tag['class']):
                        break
                except KeyError:
                    break
            for super_tag in list_tag.find_all('sup'):
                super_tag.clear()
            for list_element in list_tag.find_all('li'):
                for audio_tag in list_element.find_all('div', {'class': 'mediaContainer'}):
                    audio_links.append(audio_tag.find('source')['src'])
                    audio_tag.extract()
                for nested_list_element in list_element.find_all('ul'):
                    nested_list_element.extract()
                if list_element.text and not list_element.find('table', {'class': 'audiotable'}):
                    pronunciation_text.append(list_element.text.strip())
            pronunciation_list.append((pronunciation_index, pronunciation_text, audio_links))
        return pronunciation_list

    def parse_definitions(self, word_contents):
        definition_id_list = self.get_id_list(word_contents, 'definitions')
        definition_list = []
        definition_tag = None
        for def_index, def_id, def_type in definition_id_list:
            definition_text = []
            span_tag = self.soup.find_all('span', {'id': def_id})[0]
            table = span_tag.parent.find_next_sibling()
            while table and table.name not in ['h3', 'h4', 'h5']:
                definition_tag = table
                table = table.find_next_sibling()
                if definition_tag.name == 'p':
                    definition_text.append(definition_tag.text.strip())
                if definition_tag.name in ['ol', 'ul']:
                    for element in definition_tag.find_all('li', recursive=False):
                        if element.text:
                            definition_text.append(element.text.strip())
            if def_type == 'definitions':
                def_type = ''
            definition_list.append((def_index, definition_text, def_type))

        return definition_list

    def parse_examples(self, word_contents):
        definition_id_list = self.get_id_list(word_contents, 'definitions')
        example_list = []
        for def_index, def_id, def_type in definition_id_list:
            span_tag = self.soup.find_all('span', {'id': def_id})[0]
            table = span_tag.parent
            while (table is not None) and (table.name != 'ol'):
                table = table.find_next_sibling()
            examples = []
            while (table is not None) and (table.name == 'ol'):
                for element in table.find_all('dd'):
                    example_text = re.sub(r'\([^)]*\)', '', element.text.strip())
                    if example_text:
                        examples.append(example_text)
                    element.clear()
                example_list.append((def_index, examples, def_type))
                for quot_list in table.find_all(['ul', 'ol']):
                    quot_list.clear()
                table = table.find_next_sibling()
        return example_list

    def parse_etymologies(self, word_contents):
        etymology_id_list = self.get_id_list(word_contents, 'etymologies')
        etymology_list = []
        etymology_tag = None
        for etymology_index, etymology_id, _ in etymology_id_list:
            etymology_text = ''
            span_tag = self.soup.find_all('span', {'id': etymology_id})[0]
            next_tag = span_tag.parent.find_next_sibling()
            while (next_tag is not None) and (next_tag.name not in ['h3', 'h4', 'div', 'h5']):
                etymology_tag = next_tag
                next_tag = next_tag.find_next_sibling()
                if etymology_tag.name == 'p':
                    etymology_text += etymology_tag.text
                else:
                    for list_tag in etymology_tag.find_all('li'):
                        etymology_text += list_tag.text + '\n'
            etymology_list.append((etymology_index, etymology_text))
        return etymology_list

    def parse_related_words(self, word_contents):
        relation_id_list = self.get_id_list(word_contents, 'related')
        related_words_list = []
        for related_index, related_id, relation_type in relation_id_list:
            words = []
            span_tag = self.soup.find_all('span', {'id': related_id})[0]
            parent_tag = span_tag.parent
            while not parent_tag.find_all('li'):
                parent_tag = parent_tag.find_next_sibling()
            for list_tag in parent_tag.find_all('li'):
                words.append(list_tag.text)
            related_words_list.append((related_index, words, relation_type))
        return related_words_list

    def map_to_object(self, word_data):
        json_obj_list = []
        if not word_data['etymologies']:
            word_data['etymologies'] = [('', '')]
        for (current_etymology, next_etymology) in zip_longest(word_data['etymologies'], word_data['etymologies'][1:], fillvalue=('999', '')):
            data_obj = WordData()
            data_obj.etymology = current_etymology[1]
            for pronunciation_index, text, audio_links in word_data['pronunciations']:
                if (self.count_digits(current_etymology[0]) == self.count_digits(pronunciation_index)) or (current_etymology[0] <= pronunciation_index < next_etymology[0]):
                    data_obj.pronunciations = text
                    data_obj.audio_links = audio_links
            for definition_index, definition_text, definition_type in word_data['definitions']:
                if current_etymology[0] <= definition_index < next_etymology[0]:
                    def_obj = Definition()
                    def_obj.text = definition_text
                    def_obj.part_of_speech = definition_type
                    for example_index, examples, _ in word_data['examples']:
                        if example_index.startswith(definition_index):
                            def_obj.example_uses = examples
                    for related_word_index, related_words, relation_type in word_data['related']:
                        if related_word_index.startswith(definition_index):
                            def_obj.related_words.append(RelatedWord(relation_type, related_words))
                    data_obj.definition_list.append(def_obj)
            json_obj_list.append(data_obj.to_json())
        return json_obj_list

    def get_hrefs(self, tag) -> List[WikiWord]:
        output = []  # type: List[WikiWord]
        # print("look for hrefs")
        for link in tag.select('i.Latn.mention a'):
            href = link.get('href')
            if href is not None:
                match = re.match(MyWiktionaryParser.LINK_PARSER, href)
                if match:
                    output.append(WikiWord(word=match.group(1), language=match.group(4)))
        # print("get_hrefs", tag, output)
        return output

    def get_lemma_parts(self, tag) -> Tuple[List[Union[str, List]], Optional[str]]:
        lemma = None
        output = []
        for child in tag.findChildren(recursive=False):  # ignores text children. Use .children to cindlue them
            if child.name == 'a':
                if not child.has_attr('title'):
                    print("!" * 20, "ERROR: Found weird anchor missing title", child)
                elif child['title'] != 'Appendix:Glossary':
                    print("!" * 20, "ERROR: Found weird anchor, not glossary", child)
                else:
                    output.append(child.text)
            elif child.name == 'span':
                if child.has_attr('class'):
                    child_classes = child['class']
                    if child_classes[0] == 'inflection-of-conjoined':
                        child_parts, child_lemma = self.get_lemma_parts(child)
                        output.append(child_parts)
                    elif child_classes[0] == 'inflection-of-sep':
                        pass  # ignore separator
                    elif child_classes[0] == 'form-of-definition-link':
                        lemma = child.text
                    else:
                        print("!" * 20, "ERROR: Unknown class", child)
                else:
                    print("!" * 20, "ERROR: span missing class", child)
            else:
                print("!" * 20, "WARNING: get_lemma_parts skipping unexpected child tag", child)
        # print("get parts returning", output, lemma)
        return output, lemma


    def get_lemma_data(self, language) -> List[LemmaResults]:
        contents = self.soup.find_all('span', {'class': 'toctext'})
        word_contents = []
        start_index = None
        for content in contents:
            if content.text.lower() == language:
                start_index = content.find_previous().text + '.'
        if len(contents) != 0 and not start_index:
            return []
        for content in contents:
            index = content.find_previous().text
            content_text = self.remove_digits(content.text.lower())
            if index.startswith(start_index) and content_text in self.PARTS_OF_SPEECH:
                word_contents.append(content)

        # print(self.current_word, "word contents", word_contents)
        id_list = []

        checklist = self.PARTS_OF_SPEECH[:-2]


        if len(word_contents) == 0:
            id_list = [('1', x.title(), x) for x in checklist if self.soup.find('span', {'id': x.title()})]
        for content_tag in word_contents:
            content_index = content_tag.find_previous().text
            text_to_check = self.remove_digits(content_tag.text).strip().lower()
            if text_to_check in checklist:
                content_id = content_tag.parent['href'].replace('#', '')
                id_list.append((content_index, content_id, text_to_check))
        # print(self.current_word, "id list", id_list)

        all_lemmas = []  # type: List[LemmaResults]
        for def_index, def_id, def_type in id_list:
            # an infinitive will have no entries
            definition_text = []
            span_tag = self.soup.find_all('span', {'id': def_id})[0]
            # print("span_tag for", def_id, span_tag)
            table = span_tag.parent.find_next_sibling()
            # print("next sib", def_id, table)

            found_lemma = False

            while table and table.name not in ['h3', 'h4', 'h5']:
                # print("look for links in", table)
                inflection_lemma = None
                for span in table.select('li span.form-of-definition.use-with-mention'):
                    # NOTE see "ver" for infinitive example
                    # see "era" for noun in lemma form, conjoined example
                    # print(self.current_word, def_type, "form span:")
                    # print(span.prettify())
                    if not span.text.startswith('inflection of'):
                        parts, lemma = self.get_lemma_parts(span)
                        if lemma is None:
                            lemma = inflection_lemma
                        all_lemmas.append(LemmaResults(type=def_type, lemma=lemma, parts=parts))
                    else:
                        parts, inflection_lemma = self.get_lemma_parts(span)
                    found_lemma = True
                    # all_links += self.get_hrefs(table)
                # lemma_result = LemmaResults()
                table = table.find_next_sibling()
            if not found_lemma:
                # print(self.current_word, def_type, "no defs found, must be lemma")
                all_lemmas.append(LemmaResults(type=def_type, lemma=self.current_word, parts=[]))
            # print()
        # print(self.current_word, "get_lemmas returning", "=" * 40)
        return all_lemmas

    def get_link_data(self, language) -> List[WikiWord]:
        contents = self.soup.find_all('span', {'class': 'toctext'})
        word_contents = []
        start_index = None
        for content in contents:
            if content.text.lower() == language:
                start_index = content.find_previous().text + '.'
        if len(contents) != 0 and not start_index:
            return []
        for content in contents:
            index = content.find_previous().text
            content_text = self.remove_digits(content.text.lower())
            if index.startswith(start_index) and content_text in self.INCLUDED_ITEMS:
                word_contents.append(content)

        # print("word contents", word_contents)
        id_list = []

        checklist = ['etymology'] + self.PARTS_OF_SPEECH + self.RELATIONS

        if len(word_contents) == 0:
            id_list = [('1', x.title(), x) for x in checklist if self.soup.find('span', {'id': x.title()})]
        for content_tag in word_contents:
            content_index = content_tag.find_previous().text
            text_to_check = self.remove_digits(content_tag.text).strip().lower()
            if text_to_check in checklist:
                content_id = content_tag.parent['href'].replace('#', '')
                id_list.append((content_index, content_id, text_to_check))
        # print("id list", id_list)

        all_links = []  # type: List[WikiWord]
        for def_index, def_id, def_type in id_list:
            definition_text = []
            span_tag = self.soup.find_all('span', {'id': def_id})[0]
            # print("span_tag for", def_id, span_tag)
            table = span_tag.parent.find_next_sibling()
            # print("next sib", def_id, table)
            while table and table.name not in ['h3', 'h4', 'h5']:
                # print("look for links in", table, self.get_hrefs(table))
                all_links += self.get_hrefs(table)
                table = table.find_next_sibling()
        # print("get_link_data returning", all_links)
        return all_links

    # def parse_links(self, word_contents):
    #     lang_span = self.soup.find('span', {'id': self.language[0].upper() + self.language[1:]})
    #     print("got span", lang_span)
    #     return lang_span

    LINK_PARSER = r"\/wiki\/(-?([a-zA-ZÀ-ž]*(%[0-9A-Fa-f][0-9A-Fa-f])*)+-?)#([a-zA-ZÀ-ž]+)$"

    def fetch_links(self, word, language=None) -> List[WikiWord]:
        language = self.language if not language else language
        self.prepare_soup(word)
        return self.get_link_data(language.lower())

    def create_soup(self, response):
        self.soup = BeautifulSoup(response.text.replace('>\n<', '><'), 'lxml')

    def prepare_soup(self, word):
        response = self.session.get(self.url.format(word))
        self.create_soup(response)
        self.current_word = word
        self.clean_html()

    def fetch(self, word, language=None):
        language = self.language if not language else language
        self.prepare_soup(word)
        return self.get_word_data(language.lower())

    def fetch_lemma(self, wiki_word: WikiWord) -> List[LemmaResults]:
        self.prepare_soup(wiki_word['word'])
        return self.get_lemma_data(wiki_word['language'].lower())

    def fetch_word(self, wiki_word: WikiWord) -> WikiResults:
        self.prepare_soup(wiki_word['word'])
        return WikiResults(word_data=self.get_word_data(wiki_word['language'].lower()),
                           links=self.get_link_data(wiki_word['language'].lower()))

    # returns a list of word data lists
    def fetch_recursive(self, max_defs: int, base: str, lemma: Optional[str], language: str, cache_engine) -> List[WikiDefinition]:
        if not hasattr(cache_engine, 'wiktionary_cache'):
            cache_engine.wiktionary_cache = {}
        to_research = [WikiWord(word=base, language=language)]
        if lemma is not None:
            to_research.append(WikiWord(word=lemma, language=language))

        definitions = []  # type: List[WikiDefinition]
        while (len(definitions) < max_defs) and (len(to_research) > 0):
            self._fetch_next(max_defs, source_words=to_research, definitions=definitions, cache_engine=cache_engine)
        return definitions

    @staticmethod
    def already_defined(wiki_word: WikiWord, definitions: List[WikiDefinition]):
        for definition in definitions:
            if wiki_words_equals(definition['wiki_word'], wiki_word):
                return True
        return False

    def _fetch_next(self, max_defs: int, source_words: List[WikiWord], definitions: List[WikiDefinition], cache_engine):
        # print("_fetch_next", source_words)
        to_research = []
        for wiki_word in source_words:
            # print("consider", wiki_word)
            if not MyWiktionaryParser.already_defined(wiki_word, definitions):
                # print("wordnot defined", wiki_word)
                word_len = len(wiki_word['word'].replace('-',''))
                if (word_len > 2) and (wiki_word['language'].lower() != 'english'):
                    key = str(f"{wiki_word['word']}:{wiki_word['language'].lower()}")
                    results = cache_engine.wiktionary_cache.get(key, None)
                    if results is None:
                        print(f"<p>wiki look up of {key}</p>")
                        results = self.fetch_word(wiki_word)
                        cache_engine.wiktionary_cache[key] = results
                        cache_engine.bump_dirty()
                    # else:
                    #     print("using cache", key, results)
                    to_research += results['links']
                    definitions.append(WikiDefinition(wiki_word=wiki_word, definition=results['word_data']))
            # else:
            #     # print("alreadydefined", wiki_word)
            #     MyWiktionaryParser.already_defined(wiki_word, definitions, True)

        source_words.clear()
        source_words.extend(to_research)


class MockWiktionaryCache:
    def bump_dirty(self):
        pass


if __name__ == '__main__':
    parser = MyWiktionaryParser()
    parser.set_default_language('spanish')
    cache_engine = MockWiktionaryCache()
    output = parser.fetch_recursive(10, 'estar', None, 'spanish', cache_engine)
    print('output', output)
    print('cache enine', cache_engine)

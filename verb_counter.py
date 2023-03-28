import os
import pickle
from typing import Optional

import ebooklib
import spacy
from ebooklib import epub

from spacy.tokens import Token

from lemma_lookup import LemmaLookup
from util import language_to_code, is_text_chapter, chapter_to_str, unpersonal_parts
from pickling_base import PicklingBaseClass


class VerbCounter(PicklingBaseClass):
    def __init__(self, language: str):
        self._hits_by_word = {}
        self._first_context_by_word = {}
        super().__init__(language)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle baz
        # del state["_nearby_words"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Add baz back since it doesn't exist in the pickle
        # self._nearby_word_info = None

    def add(self, token: Token, chapter: int):
        if not token.is_alpha:
            return
        key = token.text.lower()
        if (token.pos_ == 'VERB') or (token.pos_ == 'AUX'):
            if key not in self._hits_by_word:
                self._hits_by_word[key] = 1
                self._first_context_by_word[key] = (chapter, str(token.sent))
            else:
                self._hits_by_word[key] += 1

    @staticmethod
    def load(language: str) -> Optional["VerbCounter"]:
        return PicklingBaseClass.s_load_if_exists(language, VerbCounter)


def get_verb_count(language: str, books: [str]) -> VerbCounter:
    counter = VerbCounter.load(language)
    # counter = None
    if counter is not None:
        return counter
    print("no cache, counting the hard way")

    nlp = spacy.load(language_to_code(language) + "_core_news_lg")

    for book_path in books:
        input_path = f"{language}/{book_path}"
        book = epub.read_epub(input_path)
        # items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        chapter_num = 0
        counter = VerbCounter(language)

        for item in all_items:
            if is_text_chapter(item, language):
                chapter_num += 1
                print(f"chapter {chapter_num} length is {len(item.get_body_content())}")
                text = chapter_to_str(item)
                doc = nlp(text)
                for sent in doc.sents:
                    for token in sent:
                        counter.add(token, chapter_num)
                print("counted chapter", chapter_num)
            else:
                print("skip chapter", item.get_name())

        counter.save()

    return counter


def dump_verbs(language: str, books: [str]):
    """
    Show information about verbs in the text
    :param language:
    :param books:
    :return:
    """
    lemma_lookup = LemmaLookup.load(language)

    counter = get_verb_count(language, books)
    top_verbs = [(x, y) for x, y in counter._hits_by_word.items()]
    top_verbs.sort(key=lambda x: -x[1])
    # test_cases = [0, 1, 2, 3, 4, 10, 50]
    # 22 69 1 vamos: Vamos, uno era incluso mayor que él, ¡y vestía una capa verde esmeralda! ¡Qué valor!
    # for i in [121, 146, 254, 265]: # range(0, 1000):

    uses_by_parts = HitCounter()
    uses_by_lemma_and_parts = HitCounter()

    for i in range(0, len(top_verbs)):
        wd, count = top_verbs[i]
        chapt, sent = counter._first_context_by_word[wd]
        all_lemmas = lemma_lookup.get_lemmas(wd)

        """Do two things:
        First, remove the person from the parts
        Next, create a list of the most common verb + parts
        AND a list of the most common parts
        Remember where they come from (wd, chapt, sent) as well as the lemma and parts
        """
        verb_lemas = [x for x in all_lemmas if x['type'] == 'verb']
        context = f"{wd}:{count}/{chapt}: {sent}"
        if len(verb_lemas) > 0:
            verb_lemma = verb_lemas[0]  # just use the first to keep things simple.
            parts = verb_lemma['parts']
            if len(parts) == 0:
                parts = ['infinitive']
            parts_key = unpersonal_parts(verb_lemma['parts'])
            uses_by_parts.add_hit(parts_key, context)
            uses_by_lemma_and_parts.add_hit(verb_lemma['lemma'] + ":" + parts_key, context)
    # now print the results
    print("top usage by parts")
    uses_by_parts.dump(1000)

    print("top usage by parts and lemma")
    uses_by_lemma_and_parts.dump(100)


class HitCounter:
    def __init__(self):
        self.hits_by_key = {}

    def add_hit(self, key:str, context:str):
        if key in self.hits_by_key:
            self.hits_by_key[key]['hits'] += 1
        else:
            self.hits_by_key[key] = {'hits': 1, 'first_context': context}

    def dump(self, max_entries):
        hits_and_context = [(x['hits'], x['first_context'], k) for k, x in self.hits_by_key.items()]
        hits_and_context.sort(key=lambda x: -x[0])
        hits_and_context = hits_and_context[0:max_entries]
        for hit in hits_and_context:
            print(hit[0], hit[2], hit[1])


if __name__ == '__main__':
    dump_verbs('spanish', ['books/(Harry Potter 1) Rowling, J K.epub'])


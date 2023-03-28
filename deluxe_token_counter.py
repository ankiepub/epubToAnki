import os
import pickle
from typing import TypedDict, Dict, List, Optional

import ebooklib
import spacy
from ebooklib import epub

from spacy.tokens import Token

from all_names import harry_potter_name_map
from pickling_base import PicklingBaseClass
from util import get_books, language_to_code, is_text_chapter, chapter_to_str


class FirstLemmaHit(TypedDict):
    text: str
    sent: str
    book: int
    chapter: int


class DeluxeLemmaHit(TypedDict):
    lemma: str
    hits: int
    first_hit_info: FirstLemmaHit
    texts: Dict[str, FirstLemmaHit]
    first_hit_by_part_of_speech: Dict[str, FirstLemmaHit]


class DeluxeTokenCounter(PicklingBaseClass):
    """
    This is the final version of a token counter, intended to count tokens across all books in a set.
    This version remembers where it first saw a word and also knows about lemmas provided by spacy.
    Note that spacy lemmas are much less sophisticated than wiktionary lemmas.
    """
    def __init__(self, language: str):
        self._hits_by_lemma: Dict[str, DeluxeLemmaHit] = {}
        self._lemmas_by_frequency: List[str] = []
        super().__init__(language)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle baz
        del state["_lemmas_by_frequency"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Add baz back since it doesn't exist in the pickle
        self._lemmas_by_frequency = []

    def get_hit_info(self, lemma) -> Optional[DeluxeLemmaHit]:
        return self._hits_by_lemma.get(lemma, None)

    def get_lemmas_by_frequency(self) -> List[str]:
        if len(self._lemmas_by_frequency) == 0:
            self._lemmas_by_frequency = list(self._hits_by_lemma.keys())
            lemma_map = self._hits_by_lemma
            self._lemmas_by_frequency = sorted(self._lemmas_by_frequency, key=lambda x: lemma_map[x]['hits'],
                                               reverse=True)
        return self._lemmas_by_frequency

    def add(self, token: Token, book: int, chapter: int):
        if (not token.is_alpha) or token.is_stop:
            return
        key = token.lemma_.lower()
        text_key = token.text.lower()
        part_of_speech = token.pos_
        first_hit_info = FirstLemmaHit(text=token.text, sent=token.sent.text, book=book, chapter=chapter)
        if key not in self._hits_by_lemma:
            self._hits_by_lemma[key] = DeluxeLemmaHit(hits=1, first_hit_info=first_hit_info,
                                                      lemma=token.lemma_,
                                                      texts={text_key: first_hit_info},
                                                      first_hit_by_part_of_speech={part_of_speech: first_hit_info})
        else:
            lemma_hit = self._hits_by_lemma[key]
            lemma_hit['hits'] += 1
            if text_key not in lemma_hit['texts']:
                lemma_hit['texts'][text_key] = first_hit_info
            if part_of_speech not in lemma_hit['first_hit_by_part_of_speech']:
                lemma_hit['first_hit_by_part_of_speech'][part_of_speech] = first_hit_info

    @staticmethod
    def load(language: str) -> Optional["DeluxeTokenCounter"]:
        return PicklingBaseClass.s_load_if_exists(language, DeluxeTokenCounter)


def get_deluxe_word_count(language: str) -> DeluxeTokenCounter:
    books = get_books(language)
    counter = DeluxeTokenCounter.load(language)
    if counter is not None:
        return counter
    print("no cache, counting the hard way")

    nlp = spacy.load(language_to_code(language) + "_core_news_lg")

    counter = DeluxeTokenCounter(language)

    i_book = 0
    for input_path in books:
        i_book += 1
        print("=" * 40, "read book", i_book, input_path)
        book = epub.read_epub(input_path)
        # items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        chapter_num = 0

        for item in all_items:
            if is_text_chapter(item, language):
                chapter_num += 1
                print(f"chapter {chapter_num} length is {len(item.get_body_content())}")
                text = chapter_to_str(item)
                doc = nlp(text)
                for sent in doc.sents:
                    for token in sent:
                        if token.is_alpha and not token.is_stop:
                            counter.add(token, i_book, chapter_num)
                print("counted chapter", chapter_num)
            else:
                print("skip chapter", item.get_name())

        counter.save()

    return counter


def deluxe_hit_is_proper_noun(hit: DeluxeLemmaHit) -> bool:
    if hit['lemma'].lower() in harry_potter_name_map:
        return True
    return False

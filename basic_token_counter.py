import os
import pickle
from typing import Optional

import ebooklib
import spacy
from ebooklib import epub

from spacy.tokens import Token

from pickling_base import PicklingBaseClass
from util import language_to_code, is_text_chapter, chapter_to_str


class BasicTokenCounter(PicklingBaseClass):
    """
    Version 2 of word counter. Not the final form.
    This version knows about lemmas and nearby words (similar spelling).
    """
    def __init__(self, language: str):
        self._hits_by_lemma = {}
        self._nearby_word_info = None
        super().__init__(language)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle baz
        del state["_nearby_words"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Add baz back since it doesn't exist in the pickle
        self._nearby_word_info = None

    def get_nearby_word_info(self):
        if self._nearby_word_info is None:
            by_first_2 = {}
            by_last_4 = {}
            self._nearby_word_info = (by_first_2, by_last_4)

            for word in self._hits_by_lemma.keys():
                first_2 = word[:2]
                if first_2 not in by_first_2:
                    by_first_2[first_2] = []
                by_first_2[first_2].append(word)

                last_4 = word[-4:]
                if last_4 not in by_last_4:
                    by_last_4[last_4] = []
                by_last_4[last_4].append(word)

            for word_list in by_first_2.values():
                word_list.sort()

            for word_list in by_last_4.values():
                word_list.sort(key=lambda x: x[::-1])

        return self._nearby_word_info

    def get_nearest_index(self, list, word, reversed):
        if reversed:
            for i in range(0, len(list)):
                if list[i][::-1] >= word[::-1]:
                    return i
            return len(list)
        else:
            for i in range(0, len(list)):
                if list[i] >= word:
                    return i
            return len(list)

    def has_nearby_words(self, word):
        # if it is two letters long, return true
        if len(word) < 3:
            return True
        # otherwise, if it matches all but the last N letters of a word, return true
        extra_letters = 2
        if len(word) <= 4:
            extra_letters = 1
        l1 = len(word)

        by_first2, by_last_4 = self.get_nearby_word_info()
        same_start_words = by_first2.get(word[:2], [])
        for other in same_start_words:
            l2 = len(other)
            if abs(l2 - l1) <= extra_letters:
                l_targ = max(l1, l2) - extra_letters
                if other[:l_targ] == word[:l_targ]:
                    if other != word:
                        return True
        return False

    def get_nearby_words(self, word):
        by_first2, by_last_4 = self.get_nearby_word_info()
        l1 = by_first2.get(word[:2], [])
        l2 = by_last_4.get(word[-4:], [])
        output = []

        reversed = False
        for l in (l1, l2):
            i = self.get_nearest_index(l, word, reversed)
            reversed = not reversed
            rad = 3
            i_start = max(i - rad, 0)
            i_end = min(i + rad + 1, len(l))
            output.append(l[i_start:i_end])
        return output

    def count(self) -> int:
        num = 0
        for val in self._hits_by_lemma.values():
            num += val
        return num

    def count_unique(self) -> int:
        return len(list(self._hits_by_lemma.values()))

    def count_by_hits(self, i: int) -> int:
        num = 0
        for val in self._hits_by_lemma.values():
            if val == i:
                num += 1
        return num

    def get_hits_by_lemma(self, lemma: str) -> int:
        hits = self._hits_by_lemma.get(lemma.lower(), 0)
        if hits < 2:
            if self.has_nearby_words(lemma):
                # print("adding nearby:", lemma)
                hits = 2
        return hits

    def add(self, token: Token):
        if not token.is_alpha:
            return
        key = token.lemma_.lower()
        if key not in self._hits_by_lemma:
            self._hits_by_lemma[key] = 1
        else:
            self._hits_by_lemma[key] += 1

    @staticmethod
    def load(language: str) -> Optional["BasicTokenCounter"]:
        return PicklingBaseClass.s_load_if_exists(language, BasicTokenCounter)


def get_basic_word_count(language: str, books: [str]) -> BasicTokenCounter:
    counter = BasicTokenCounter.load(language)
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
        counter = BasicTokenCounter(language)

        for item in all_items:
            if is_text_chapter(item, language):
                chapter_num += 1
                print(f"chapter {chapter_num} length is {len(item.get_body_content())}")
                text = chapter_to_str(item)
                doc = nlp(text)
                for sent in doc.sents:
                    for token in sent:
                        counter.add(token)
                print("counted chapter", chapter_num)
            else:
                print("skip chapter", item.get_name())

        counter.save()

    return counter

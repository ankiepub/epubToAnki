from typing import Dict, Optional

import ebooklib
from ebooklib import epub

from util import is_text_chapter, chapter_to_str
from pickling_base import PicklingBaseClass
from spacy import Language as SpacyLanguage

class RawWordCounter(PicklingBaseClass):
    """
    UNUSED
    Original word counter.
    Simple boolean dictionary.
    """
    def __init__(self, language: str):
        self._words_seen: Dict[str, bool] = {}
        super().__init__(language)

    def contains_word(self, the_word: str) -> bool:
        return the_word in self._words_seen

    def add(self, the_word: str):
        self._words_seen[the_word] = True

    @staticmethod
    def load(language: str) -> Optional["RawWordCounter"]:
        return PicklingBaseClass.s_load_if_exists(language, RawWordCounter)


def get_raw_word_count(language: str, books: [str], nlp: SpacyLanguage) -> RawWordCounter:
    counter = RawWordCounter.load(language)
    if counter is not None:
        return counter
    print("no cache, counting raw the hard way")

    for book_path in books:
        input_path = f"{language}/{book_path}"
        book = epub.read_epub(input_path)
        # items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        chapter_num = 0
        counter: RawWordCounter = RawWordCounter(language)

        for item in all_items:
            if is_text_chapter(item, language):
                chapter_num += 1
                print(f"chapter {chapter_num} length is {len(item.get_body_content())}")
                text = chapter_to_str(item)
                doc = nlp(text)
                for sent in doc.sents:
                    for token in sent:
                        counter.add(token.text)
                print("counted chapter", chapter_num)
            else:
                print("skip chapter", item.get_name())

        counter.save()

    return counter

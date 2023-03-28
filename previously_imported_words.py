import csv
import os
import pickle
from typing import Dict

from deluxe_token_counter import DeluxeLemmaHit
from lemma_lookup import LemmaLookup
from pickling_base import PicklingBaseClass

from util import get_biggest_word

class PreviouslyImportedWords(PicklingBaseClass):
    def __init__(self, language: str):
        self._seen_words: Dict[str, bool] = {}
        self._seen_words_and_lemmas: Dict[str, bool] = {}
        self._seen_csv_paths: Dict[str, bool] = {}
        super().__init__(language)

    def get_all_seen_words(self) -> [str]:
        return list(self._seen_words.keys())

    def has_seen_word_or_lemma(self, text: str) -> bool:
        return text.lower() in self._seen_words_and_lemmas

    def has_seen_info(self, info: DeluxeLemmaHit):
        if self.has_seen_word_or_lemma(info['lemma']):
            return True
        for key in info['texts'].keys():
            if self.has_seen_word_or_lemma(key):
                return True
        return False

    def add(self, text: str, lemma_lookup: "LemmaLookup"):
        self._seen_words[text.lower()] = True
        self._seen_words_and_lemmas[text.lower()] = True
        for lemma_info in lemma_lookup.get_lemmas(text):
            self._seen_words_and_lemmas[get_biggest_word(lemma_info['lemma'].lower())] = True

    def add_file(self, file_path, lemma_lookup: "LemmaLookup"):
        if file_path.endswith('.csv'):
            separator = ','
        elif file_path.endswith('.tsv'):
            separator = '\t'
        else:
            return
        with open(file_path, mode='r') as fin:
            csv_file = csv.reader(fin, delimiter=separator)
            for row in csv_file:
                self.add(row[0], lemma_lookup)

    def add_new_files(self, lemma_lookup: "LemmaLookup", save: bool = True):
        root_path = os.path.join(self.language, 'already_imported')
        for file in os.listdir(root_path):
            if file not in self._seen_csv_paths:
                self.add_file(os.path.join(root_path, file), lemma_lookup)
                self._seen_csv_paths[file] = True
        if save:
            self.save()

    @staticmethod
    def load(language: str) -> "PreviouslyImportedWords":
        return PicklingBaseClass.s_load(language, PreviouslyImportedWords)

    @staticmethod
    def load_and_update(language: str, lemma_lookup: "LemmaLookup") -> "PreviouslyImportedWords":
        counter = PreviouslyImportedWords.load(language)
        counter.add_new_files(lemma_lookup)
        return counter

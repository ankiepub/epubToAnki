from my_wiktionary_parser import MyWiktionaryParser as WiktionaryParser
from my_wiktionary_parser import LemmaResults
from my_wiktionary_parser import WikiWord

from pickling_base import PicklingBaseClass
from typing import List, Optional
from util import get_biggest_word
from spacy.tokens.token import Token


_pos_to_type = {
    'VERB': 'verb',
    'AUX': 'verb',
    'NOUN': 'noun',
    'ADV': 'adverb',
    'ADJ': 'adjective',
    'PROPN': 'noun',
    'DET': 'determiner',
    'PRON': 'pronoun',
    'INTJ': 'interjection',
    'NUM': 'numeral',
    'SCONJ': 'conjunction',
    'CCONJ': 'conjunction',
}


def token_to_wiktionary_type(token: Token) -> str:
    return _pos_to_type.get(token.pos_, 'unknown')


class LemmaLookup(PicklingBaseClass):
    """
    This class looks up lemmas from Wiktionary.
    It uses WiktionaryParser to get the Wiktionary entry for a word and then parses the response to extract
    lemmas and parts of speach.
    Lookups are saved in the pickle cache.
    """
    def __init__(self, language: str):
        self.language = language
        self._lemmas_by_word = {}
        self.parser = WiktionaryParser()
        self.parser.set_default_language(language)
        self.parser.exclude_relation("related terms")
        self.dirty_count = 0
        super().__init__(language)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle these
        del state["parser"]
        del state['dirty_count']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.parser = WiktionaryParser()
        self.parser.set_default_language(self.language)
        self.parser.exclude_relation("related terms")
        self.dirty_count = 0
        # Add baz back since it doesn't exist in the pickle
        # self._nearby_word_info = None

    def _add(self, text: str, lemmas: List[LemmaResults]):
        self._lemmas_by_word[text] = lemmas

    def get_best_token_lemma(self, token: Token) -> Optional[LemmaResults]:
        """
        Given a token, return a single lemma result. This won't always be correct.
        :param token:
        :return:
        """
        all_lemmas = self.get_lemmas(token.text.lower())
        if len(all_lemmas) == 0:
            return None

        word_type = token_to_wiktionary_type(token)
        matching_lemmas = [x for x in all_lemmas if x['type'] == word_type]
        if len(matching_lemmas) == 0:
            return all_lemmas[0]
        else:
            return matching_lemmas[0]

    def get_lemmas(self, text: str) -> List[LemmaResults]:
        text = get_biggest_word(text.lower())
        if text in self._lemmas_by_word:
            return self._lemmas_by_word[text]
        else:
            print("lemma lookup fetch lemmas for", text, end='')
            lemmas = self.parser.fetch_lemma(WikiWord(word=text, language=self.language))
            print(" GOT:", str(lemmas))
            self._lemmas_by_word[text] = lemmas
            self.dirty_count += 1
            if self.dirty_count >= 20:
                self.save()
                self.dirty_count = 0
            return lemmas

    @staticmethod
    def load(language: str) -> "LemmaLookup":
        return PicklingBaseClass.s_load(language, LemmaLookup)


if __name__ == '__main__':
    lemma_lookup = LemmaLookup.load('spanish')
    print(lemma_lookup.get_lemmas('avergonzar él'))
    for key in list(lemma_lookup._lemmas_by_word.keys()):
        if len(key.split(' ')) > 1:
            print(key, "=>", lemma_lookup.get_lemmas(key))


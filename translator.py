from pickling_base import PicklingBaseClass
from typing import Callable, Protocol, Iterator, Optional, Union, Tuple, Any, overload, Dict, List

from deep_translator.base import BaseTranslator
from deep_translator import GoogleTranslator, LingueeTranslator, PonsTranslator
from deep_translator.base import BaseTranslator

from settings import get_deepl_api_key

from util import language_to_code
from deepl2 import DeeplTranslator2

_translator_engines = {}


def get_google_trans(language: str) -> GoogleTranslator:
    global _translator_engines
    key = f"goog_{language}"
    if key not in _translator_engines:
        _translator_engines[key] = GoogleTranslator(source=language_to_code(language), target='en')
    return _translator_engines[key]


def get_deepl_trans(language: str) -> DeeplTranslator2:
    global _translator_engines
    key = f"deepl_{language}"
    if key not in _translator_engines:
        api_key, use_free_api = get_deepl_api_key()
        _translator_engines[key] = DeeplTranslator2(api_key, source=language_to_code(language), target='en',
                                                    use_free_api=use_free_api)
    return _translator_engines[key]


# translations are saved in cache/<language>/Translation.pickle
class Translation(PicklingBaseClass):
    def __init__(self, language: str, data: Optional[dict] = None):
        if data is not None:
            self.data = data
        else:
            self.data = {}
        super().__init__(language)

    def _translate(self, text: str, key_prefix: str, trans: BaseTranslator, return_all: bool) -> str:
        # print("translate", language, text, key_prefix, return_all)
        key = key_prefix + text
        if key not in self.data:
            print("<p>translate", text, "</p>")
            # print("calling translate with ", text)
            self.data[key] = trans.translate(text, return_all=return_all)
            if self.data[key] is None:
                self.data[key] = text
            else:
                print("<p>", self.data[key], "</p>")
            self.dirty_count += 1

        if self.dirty_count >= 5:
            self.save()

        return self.data[key]

    def translate(self, text: str) -> str:
        # use deepl as the default translation engine
        return self.deepl_translate(text)

    # def pons_translate(self, text: str) -> str:
    #     return self._translate(text, "PONS:", Translation.pons_trans, True)
    #
    # def ling_translate(self, text: str) -> str:
    #     return self._translate(text, "LING:", Translation.ling_trans, True)

    def deepl_translate(self, text: str) -> str:
        return self._translate(text, "DEEPL:", get_deepl_trans(self.language), True)

    @staticmethod
    def load(language: str) -> "Translation":
        return PicklingBaseClass.s_load(language, Translation)


if __name__ == '__main__':
    trans = Translation.load('spanish')

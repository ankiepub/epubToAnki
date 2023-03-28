from abc import ABC
from typing import TypeVar, Optional, Type
import pickle
import os

T = TypeVar('T')


class PicklingBaseClass(ABC):
    def __init__(self, language: str):
        self.language = language
        self.dirty_count = 0

    @staticmethod
    def s_get_cache_path(language: str, klass: Type[T]) -> str:
        return f"./cache/{language}/{klass.__name__}.pickle"

    @staticmethod
    def s_load(language: str, klass: Type[T]) -> T:
        t_inst = PicklingBaseClass.s_load_if_exists(language, klass)
        if t_inst is None:
            t_inst = klass(language)
            t_inst.language = language
        return t_inst

    @staticmethod
    def s_load_if_exists(language: str, klass: Type[T]) -> Optional[T]:
        lang_path = PicklingBaseClass.s_get_cache_path(language, klass)
        try:
            if os.path.exists(lang_path):
                with open(lang_path, 'rb') as fin:
                    t_inst = pickle.load(fin)
                    t_inst.language = language
                    return t_inst
        except:
            print("error reading", lang_path)
            raise
        return None

    def get_cache_path(self) -> str:
        return PicklingBaseClass.s_get_cache_path(self.language, self.__class__)

    def save(self):
        self.dirty_count = 0
        with open(self.get_cache_path(), 'wb') as file_out:
            # dump information to that file
            pickle.dump(self, file_out)



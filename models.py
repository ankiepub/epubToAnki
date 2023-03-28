from typing import TypedDict, Dict


class LemmaInfo(TypedDict):
    book: int
    chapter: int
    sentence: str
    count: int


class WordLocInfo(TypedDict):
    lemmas: Dict[str, LemmaInfo]
    count: int

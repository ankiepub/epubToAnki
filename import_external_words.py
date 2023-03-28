"""
At one point, I downloaded and imported a list of top 5000 words.
This wasn't very useful because most of the words had no context.
The only useful words were swear words which did not appear in my text.
I will leave this code here in case it helps some future endeavor.
"""

from ebooklib import epub
from typing import Dict, List
import pickle
import os
import ebooklib

from models import WordLocInfo
from util import is_text_chapter
from bs4 import BeautifulSoup
from spacy import Language as SpacyLanguage
from raw_word_counter import get_raw_word_count
from basic_token_counter import get_basic_word_count
from translator import Translation
from csv_output import save_words_to_csv
import csv
import spacy
from util import language_to_code


def get_word_map(language: str, books: [str], nlp: SpacyLanguage) -> Dict[str, WordLocInfo]:
    """
    This function finds the first instance of a word in all the books.
    :param language:
    :param books:
    :param nlp:
    :return:
    """
    cache_path = f"./cache/{language}/word_map.pickle"
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as fin:
            return pickle.load(fin)

    word_to_first_location:Dict[str, WordLocInfo] = {}
    book_id = 0
    for book_path in books[1:]:
        book_id += 1
        input_path = book_path

        book = epub.read_epub(input_path)

        all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)

        all_items = list(filter(lambda x: is_text_chapter(x, language), all_items))

        for i in range(0, len(all_items)):
            chapter = all_items[i]
            print(f"<h1>Chapter {i + 1}: {len(chapter.get_body_content())} book {book_id}</h1>")
            soup = BeautifulSoup(chapter.get_body_content(), "html.parser")

            para_num = 0
            word_count = 0
            for para in soup.find_all('p'):
                para_num += 1
                text = para.get_text()
                doc = nlp(text)
                sent_num = 0
                for sent in doc.sents:
                    sent_num += 1
                    for token in sent:
                        if token.is_alpha:
                            word_count += 1
                            lemma_key = token.lemma_.lower()
                            word_key = token.text.lower()
                            if not token.is_stop:
                                if word_key not in word_to_first_location:
                                    word_to_first_location[word_key] = {'lemmas': {}, 'count': 0}
                                word_info = word_to_first_location[word_key]
                                word_info['count'] += 1
                                lemmas = word_info['lemmas']
                                if lemma_key not in lemmas:
                                    lemmas[lemma_key] = {'book': book_id, 'chapter': i + 1, 'sentence': sent.text, 'count': 0}
                                else:
                                    lemmas[lemma_key]['count'] += 1

    with open(cache_path, 'wb') as file_out:
        pickle.dump(word_to_first_location, file_out)
    return word_to_first_location


def import_top_5000(language: str, books: [str]):
    raw_words = get_raw_word_count(language, books)
    token_count = get_basic_word_count(language, books)
    trans = Translation.load(language)

    print("got raw words", len(raw_words._words_seen.keys()))
    path = './spanish/top_5000_spanish_words.csv'
    new_words: List[str] = []
    with open(path, 'r') as fin:
        reader = csv.reader(fin)
        word_index = 5
        for row in reader:
            the_word = row[word_index]
            if not raw_words.contains_word(the_word):
                if not token_count.get_hits_by_lemma(the_word):
                    new_words.append(the_word)

    print("new words =", len(new_words), new_words[0:100])
    nlp = spacy.load(language_to_code(language) + "_core_news_lg")
    map_word_to_sentence = get_word_map(language, books, nlp)

    # new_words # 990 total
    save_words_to_csv(language, new_words, 1000, 2000, trans, 'top_5000', map_word_to_sentence)

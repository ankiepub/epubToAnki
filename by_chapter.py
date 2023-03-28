from spacy import Language as SpacyLanguage
from bs4 import BeautifulSoup
import os
import csv
from deluxe_token_counter import get_deluxe_word_count, DeluxeTokenCounter
from lemma_lookup import LemmaLookup
from previously_imported_words import PreviouslyImportedWords
from util import get_books
from ebooklib import epub
import ebooklib
from util import is_text_chapter, get_biggest_word
from spacy.tokens.token import Token
from translator import Translation
from typing import TypedDict, List
from create_mp3 import mp3_name_from_text, create_mp3
from word_emphasis import add_token_emphasis_2
from wiktionary_cache import WiktionaryCache
import time


def token_to_text_key(token: Token) -> str:
    return token.text.lower()


def token_to_nlp_lemma_key(token: Token) -> str:
    return get_biggest_word(token.lemma_.lower())


def get_text_keys(token: Token, lemma_lookup: LemmaLookup) -> [str]:
    all_keys = [token_to_text_key(token), token_to_nlp_lemma_key(token)]

    for lemma_info in lemma_lookup.get_lemmas(token.text):
        all_keys.append(get_biggest_word(lemma_info['lemma'].lower()))
    return all_keys


def should_include_token(token: Token, words_and_lemmas_seen: {}, already_imported: PreviouslyImportedWords,
                         deluxe_word_count: DeluxeTokenCounter, lemma_lookup: LemmaLookup,
                         min_word_frequency: int) -> bool:
    if (not token.is_alpha) or token.is_stop or (len(token.text) < 2):
        return False  # don't include stop (very common) words or non-alpha words or one-letter words

    hit_info = deluxe_word_count.get_hit_info(token.lemma_.lower())
    if hit_info['hits'] < min_word_frequency:
        return False  # not enough hits

    if already_imported.has_seen_info(hit_info):
        return False

    for text_key in get_text_keys(token, lemma_lookup):
        if text_key in words_and_lemmas_seen:
            return False
        if already_imported.has_seen_word_or_lemma(text_key):
            return False

    return True


class SentenceTokens(TypedDict):
    text: str
    tokens: List[Token]


def save_chapter_tokens_to_csv(language: str, sentences: List[SentenceTokens], context: str,
                               lemma_lookup: LemmaLookup, nlp: SpacyLanguage):
    csv_dir = os.path.join(language, 'output')
    os.makedirs(csv_dir, exist_ok=True)
    file_name = f'{context}.csv'
    csv_path = os.path.join(csv_dir, file_name)

    total_tokens = sum([len(x['tokens']) for x in sentences])

    trans = Translation.load(language)
    wiktionary_etymology = WiktionaryCache.load(language)

    i_token = 0
    last_log_time = time.time()
    num_tokens_written = 0
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')

        for sentence in sentences:
            sentence_tokens_text = [x.text for x in sentence['tokens']]
            for token in sentence['tokens']:
                i_token += 1
                current_time = time.time()
                if (current_time - last_log_time) > 10.0:  # log progress every this many seconds
                    print(f"token {i_token} of {total_tokens}")
                    last_log_time = current_time
                text_cell = token.text
                translation_cell = trans.translate(token.text)
                if translation_cell.lower() != text_cell.lower():
                    num_tokens_written += 1
                    mp3_name = mp3_name_from_text(language, text_cell)
                    create_mp3(language, token.text, mp3_name)
                    audio_cell = f"[sound:{mp3_name}]"
                    sentence_cell = add_token_emphasis_2(sentence['text'], sentence_tokens_text, text_cell, nlp)
                    sentence_translated_cell = trans.translate(sentence_cell)
                    context_cell = f"{context} word {i_token} of {total_tokens}"
                    lemma_info = lemma_lookup.get_best_token_lemma(token)
                    lemma_cell = ""
                    if lemma_info is not None:
                        if lemma_info['lemma'].lower() != text_cell:
                            lemma_cell = lemma_info['lemma']
                            lemma_cell += ": " + trans.translate(lemma_info['lemma'])

                    etymology_cell = wiktionary_etymology.define_full_2(10, token.text.lower(), None)

                    # ['word', 'translation', 'audio', 'lemma', 'context', 'sample sentence', 'sample english', 'etymology']
                    row = [text_cell, translation_cell, audio_cell, lemma_cell,
                           context_cell, sentence_cell, sentence_translated_cell, etymology_cell]
                    writer.writerow(row)
    print(f"Finished writing {num_tokens_written} words to csv file: {csv_path}")
    cells = ['word', 'translation', 'audio', 'lemma', 'context', 'sample sentence', 'sample english', 'etymology']
    print(", ".join([f"{i+1}:{x}" for (i, x) in enumerate(cells)]))
    wiktionary_etymology.save()
    lemma_lookup.save()


def create_chapter_words(language: str, book_number: int, start_chapter: int, num_chapters: int,
                         min_word_frequency: int, nlp: SpacyLanguage):
    """
    Chapter by chapter, output the first appearance of a word (with a unique lemma).
    If the word does not meet our min_frequency threshold, skip it.
    If the word appears in our already_imported directory, skip it.
    :param language: the language
    :param book_number: starting at 1, which book to read from
    :param start_chapter: starting at 1, the first chapter to output
    :param num_chapters: the number of chapters to output
    :param min_word_frequency: only output words that appear at least this many times.
    :param nlp: the natural language parser
    :param include_stop_words: include stop words (most common handful of words). Default is False.
    """
    books = get_books(language)
    target_book_path = books[book_number-1]
    deluxe_word_count = get_deluxe_word_count(language)
    lemma_lookup = LemmaLookup.load('italian')
    already_imported = PreviouslyImportedWords.load_and_update('italian', lemma_lookup)
    words_and_lemmas_seen = {}  # words and lemmas seen now. Use in conjunction with already_imported

    print("read book", target_book_path)

    book = epub.read_epub(target_book_path)

    # items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    all_chapters = list(filter(lambda x: is_text_chapter(x, language), all_items))

    for chapter_num in range(start_chapter, start_chapter+num_chapters):
        i_chapter = chapter_num - 1
        if i_chapter < 0:
            print("minimum start_chapter is 1")
            continue
        if i_chapter >= len(all_chapters):
            print(f"there are only len(all_chapters). Skipping chapter index {i_chapter}")
            continue
        chapter = all_chapters[i_chapter]
        print(f"<h1>Chapter {chapter_num}: {len(chapter.get_body_content())} characters</h1>")
        # print(chapter.get_body_content()[0:1000])
        soup = BeautifulSoup(chapter.get_body_content(), "html.parser")
        sentences: List[SentenceTokens] = []

        word_count = 0
        # new_word_count_by_freq = {}
        total_words_seen = 0
        new_tokens_found = []

        for para in soup.find_all('p'):
            para_text = para.get_text()
            doc = nlp(para_text)
            for sent in doc.sents:
                sentence: SentenceTokens = {'tokens':[], 'text':sent.text}
                for token in sent:
                    if should_include_token(token=token, already_imported=already_imported, lemma_lookup=lemma_lookup,
                                            words_and_lemmas_seen=words_and_lemmas_seen,
                                            deluxe_word_count=deluxe_word_count, min_word_frequency=min_word_frequency):
                        sentence['tokens'].append(token)
                        new_tokens_found.append(token)
                        for key in get_text_keys(token, lemma_lookup):
                            words_and_lemmas_seen[key] = True
                    if token.is_alpha and (not token.is_stop):
                        total_words_seen += 1
                if len(sentence['tokens']) > 0:
                    sentences.append(sentence)

        percent_new = str(round(1000 * len(new_tokens_found) / total_words_seen) / 10)
        print(f"finished parsing chapter {chapter_num}, found {len(new_tokens_found)} new words of {total_words_seen} ({percent_new}% new)")
        if len(sentences) > 0:
            context = f"book {book_number} chapter {chapter_num}"
            save_chapter_tokens_to_csv(language, sentences, context, lemma_lookup, nlp)

    lemma_lookup.save()


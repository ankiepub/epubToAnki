import csv
from typing import Dict, List

import os

from spacy import Language as SpacyLanguage

from create_mp3 import mp3_name_from_text, create_mp3
from deluxe_token_counter import DeluxeLemmaHit
from models import WordLocInfo
from translator import Translation
from wiktionary_cache import WiktionaryCache
from word_emphasis import add_token_emphasis, fix_emphasis_tags


def save_words_to_csv(language: str, words: [str], start: int, end: int, trans: Translation, word_set: str,
                      word_loc_info: Dict[str, WordLocInfo]) -> int:
    end = min(end, len(words))
    words = words[start:end]
    file_name = f'{language}/tokens_{word_set}_{start}_to_{end}.csv'
    # print("save_tokens_to_tsv file", file_name, nlp)
    num_lines = 0

    wc = WiktionaryCache.load(language)

    with open(file_name, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter=',', lineterminator='\n')
        i_token = 0
        num_tokens = len(words)

        for token in words:
            print("="* 40, token, i_token, num_tokens)
            i_token += 1
            text = token

            mp3_name = mp3_name_from_text(language, text)
            create_mp3(language, text, mp3_name)
            audio_cell = f"[sound:{mp3_name}]"

            translation = trans.translate(text)
            sample = ""
            sample_en = ""

            word_key = text.lower()
            hits = f"word {i_token} of {num_tokens} ({round(i_token * 100 / num_tokens)}%)"
            if word_key in word_loc_info:
                word_info = word_loc_info[word_key]
                first_lemma = list(word_info['lemmas'].values())[0]
                sentence = first_lemma['sentence']
                sample = add_token_emphasis(sentence, {text}, text, first_lemma['chapter'], {sentence: [text]}, nlp)
                sample_en = fix_emphasis_tags(trans.translate(sample))
                sample = fix_emphasis_tags(sample)
                hits += f" from book {first_lemma['book']} chapter {first_lemma['chapter']}"

            alternate = ""
            num_lines += 1
            wikt_def = wc.define_full_2(10, text, None)
            writer.writerow([text, translation, sample, alternate, hits, sample_en, audio_cell, wikt_def])
    wc.save()
    return num_lines


def save_infos_to_csv(language: str, infos: List[DeluxeLemmaHit], word_set: str, nlp: SpacyLanguage) -> int:
    file_name = f'tokens_{word_set}.csv'
    file_path = os.path.join(language, 'output', file_name)
    trans = Translation.load(language)

    num_lines = 0

    wc = WiktionaryCache.load(language)

    with open(file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', lineterminator='\n')
        i_token = 0
        num_tokens = len(infos)

        for deluxe_hit in infos:
            print(f'{"="* 20} {i_token} of {num_tokens}: {deluxe_hit}')
            i_token += 1
            first_hit_info = deluxe_hit['first_hit_info']
            text = first_hit_info['text']

            mp3_name = mp3_name_from_text(language, text)
            create_mp3(language, text, mp3_name)
            audio_cell = f"[sound:{mp3_name}]"

            translation = trans.translate(text.lower())
            sentence = first_hit_info['sent']
            context_cell = f"{word_set}: word {i_token} of {num_tokens} ({round(i_token * 100 / num_tokens)}%)"
            sample = add_token_emphasis(sentence, {text}, text, first_hit_info['chapter'], {sentence: [text]}, nlp)
            translated_sentence_cell = fix_emphasis_tags(trans.translate(sample))
            sentence_cell = fix_emphasis_tags(sample)
            context_cell += f" from book {first_hit_info['book']} chapter {first_hit_info['chapter']}"
            lemma_cell = ""
            num_lines += 1
            etymology_cell = wc.define_full_2(10, text.lower(), None)

            # ['word', 'translation', 'audio', 'lemma', 'context', 'sample sentence', 'sample english', 'etymology']
            writer.writerow([text, translation, audio_cell, lemma_cell, context_cell, sentence_cell,
                             translated_sentence_cell, etymology_cell])
    wc.save()

    print(f"Finished writing {num_lines} words to csv file: {file_path}")
    cells = ['word', 'translation', 'audio', 'lemma', 'context', 'sample sentence', 'sample english', 'etymology']
    print(", ".join([f"{i+1}:{x}" for (i, x) in enumerate(cells)]))

    return num_lines

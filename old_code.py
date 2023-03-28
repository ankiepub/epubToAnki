import csv
import os
from typing import Dict

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from gtts import gTTS
from spacy import Language as SpacyLanguage
from spacy.tokens import Token

from basic_token_counter import BasicTokenCounter, get_basic_word_count
from translator import Translation
from util import language_to_code, get_biggest_word, is_text_chapter
from wiktionary_cache import WiktionaryCache
from word_emphasis import add_token_emphasis, fix_emphasis_tags
from settings import get_anki_mp3_directory

def save_tokens_to_tsv(language: str, tokens: [Token], trans: Translation, counter: BasicTokenCounter, chapter: int,
                       book_id: int, frequent_words_only: bool, nlp: SpacyLanguage) -> int:
    # print("save_tokens_to_tsv", chapter, len(tokens))

    if frequent_words_only:
        name_extension = ''
    else:
        name_extension = '_b'

    file_name = f'{language}/tokens_bk{book_id}_ch{chapter + 1}{name_extension}.tsv'
    everything_file = f'{language}/tokens_bk{book_id}_ch_all{name_extension}.tsv'
    # print("save_tokens_to_tsv file", file_name)
    num_lines = 0

    token_text_set = {x.text for x in tokens}
    seen_samples = {}

    min_freq = 2  # only use words that appear more than once
    if frequent_words_only:
        filtered_tokens = list([x for x in tokens if counter.get_hits_by_lemma(x.lemma_) >= min_freq])
    else:
        filtered_tokens = list([x for x in tokens if counter.get_hits_by_lemma(x.lemma_) < min_freq])


    wc = WiktionaryCache.load(language)

    with open(file_name, 'w', newline='') as tsvfile:
        with open(everything_file, 'a', newline='') as tsvfile2:
            writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
            writer2 = csv.writer(tsvfile2, delimiter='\t', lineterminator='\n')
            i_token = 0
            num_tokens = len(filtered_tokens)
            # create the sentence to token map
            sentence_to_tokens: Dict[str, list] = {}
            for token in filtered_tokens:
                sent = str(token.sent)
                if not sent in sentence_to_tokens:
                    sentence_to_tokens[sent] = []
                sentence_to_tokens[sent].append(str(token.text))

            for token in filtered_tokens:
                i_token += 1
                text = token.text

                mp3_name = f"{language_to_code(language)}_{text}.mp3"
                mp3_path = os.path.join(get_anki_mp3_directory(), mp3_name)
                if not os.path.exists(mp3_path):
                    tts = gTTS(text, lang=language_to_code(language))
                    print(f"<p>tts {mp3_name}</p>")
                    tts.save(mp3_path)
                audio_cell = f"[sound:{mp3_name}]"

                translation = trans.translate(token.text)
                sample = add_token_emphasis(str(token.sent), token_text_set, token.text, chapter, sentence_to_tokens, nlp)
                sample_en = fix_emphasis_tags(trans.translate(sample))
                sample = fix_emphasis_tags(sample)
                if sample not in seen_samples:
                    seen_samples[sample] = True
                    # print("<P>" + sample + "</P>")
                    # print("<P>" + sample_en + "</P>")
                alternate = ""
                if token.text != token.lemma_:
                    alternate = f"{token.lemma_}: {trans.translate(token.lemma_)}"
                num_lines += 1
                hits = f"[{counter.get_hits_by_lemma(token.lemma_)}] chapter {chapter + 1}, word {i_token} of {num_tokens} ({round(i_token * 100 / num_tokens)}%)"
                lemma = None
                if str(token.lemma_).strip() != text.strip():
                    lemma = get_biggest_word(str(token.lemma_))

                wikt_def = wc.define_full_2(7, text, lemma)

                writer.writerow([text, translation, sample, alternate, hits, sample_en, audio_cell, wikt_def])
                writer2.writerow([text, translation, sample, alternate, hits, sample_en, audio_cell, wikt_def])
    wc.save()
    return num_lines


def print_guide(language: str, books: [str], start_chapter: int, end_chapter: int, frequent_words_only: bool,
                nlp: SpacyLanguage):
    counter = get_basic_word_count(language, books)
    trans = Translation.load(language)

    seen_lemmas = {}
    seen_infos = {}

    book_id = 0
    for book_path in books:
        book_id += 1
        input_path = f"{language}/{book_path}"

        book = epub.read_epub(input_path)

        # items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        all_items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)

        all_items = list(filter(lambda x: is_text_chapter(x, language), all_items))

        all_items = all_items[0:min(end_chapter, len(all_items))]  # second chapter only for now
        chapter_data = []

        for i in range(0, len(all_items)):
            chapter = all_items[i]
            print(f"<h1>Chapter {i + 1}: {len(chapter.get_body_content())}</h1>")
            # print(chapter.get_body_content()[0:1000])
            soup = BeautifulSoup(chapter.get_body_content(), "html.parser")

            para_num = 0
            every_token = []
            word_count = 0
            new_word_count_by_freq = {}
            for para in soup.find_all('p'):
                para_num += 1
                text = para.get_text()
                para_info = {"text": text}
                # print(f"<p>{text}</p>")
                doc = nlp(text)
                sent_num = 0
                all_sent_infos = []
                all_tokens = []
                for sent in doc.sents:
                    sent_info = {'text': str(sent), 'tokens': []}
                    all_sent_infos.append(sent_info)
                    sent_num += 1
                    for token in sent:
                        if token.is_alpha:
                            word_count += 1
                            lemma_key = token.lemma_.lower()
                            if ((language != 'spanish') or (not token.is_stop)) and (lemma_key not in seen_lemmas):
                                seen_lemmas[lemma_key] = True
                                if token.text.lower() != trans.translate(token.text).lower():
                                    sent_info['tokens'].append(token)
                                    all_tokens.append(token)

                # now output our para_info
                if len(all_tokens) > 0:
                    every_token += all_tokens
                    # print(f"<h2>Paragraph {para_num}</h2>")
                    # print(f"<p class='para'>" + add_token_emphasis(text, all_tokens) + "</p>", nlp)
                    for sent_info in all_sent_infos:
                        if len(sent_info['tokens']) > 0:
                            # if len(all_sent_infos) > 1:
                            #     print("<p class='sent'>" + add_token_emphasis(sent_info['text'], sent_info['tokens']) + "</p>", nlp)
                            # print("<p class='trans'>" + trans.translate(sent_info['text']) + "</p>")
                            pass

            # print("save it", i)
            # num_new_words = save_tokens_to_tsv(language, every_token, trans, counter, i, book_id, nlp)
            num_new_words = len(every_token)
            if (i + 1) >= start_chapter:
                num_new_words_2 = save_tokens_to_tsv(language, every_token, trans, counter, i, book_id, frequent_words_only, nlp)
                print(
                    f"FINISHED BOOK {book_id} CHAPTER {i + 1}, {word_count} words, {num_new_words} new ({round(100 * num_new_words / word_count)}%), of which {num_new_words_2} ({round(100 * num_new_words_2 / word_count)}%) used more than once")
                chapter_data.append((word_count, num_new_words_2 / 50.0))
            trans.save(language)
            # print(f" - {num_new_words_2} words that appear more than once, {}% new more than once words")
            # first_n_hits = [f"{x}: {new_word_count_by_freq.get(x)}" for x in range(0, 4)]
            #
            # print(f"word count by frequency: {first_n_hits}")
        total = 0
        for row in chapter_data:
            print(row[0], row[1])
            total += row[1]


def test_definitions():
    import html2text
    html2 = html2text.HTML2Text()

    wc = WiktionaryCache.load('spanish')

    # html_output = wc.to_html(wc.parser.fetch('celo', 'Latin'), 'celo', 'Latin')
    definitions = wc.parser.fetch_recursive(7, 'celo', None, 'Latin', wc)
    lines = [WiktionaryCache.to_html(x['definition'], x['wiki_word']['word'], x['wiki_word']['language']) for x in
             definitions]
    print('\n'.join(lines))
    return

    # wc.wiktionary_cache = {}
    # wc.save()

    # html_output = wc.define_full_2(7, 'superior', None)

    print(html2.handle(html_output))
    return
    # if True:
    #     for key in list(wc.definitions.keys()):
    #         output = wc.define_full_list(6, key, lemma=None, source="")
    #         output = list(filter(lambda x: len(x.strip()) > 0, output))
    #         if len(output) < 1:
    #             print("NO DEFINITION: ", key, wc.sources.get(key, None))
    #         elif len(output) < 2:
    #             if not WiktionaryCache.contains_reference_to_other_language(output[0]):
    #                 print(output[0])
    #         # if not WiktionaryCache.contains_reference_to_other_language(output):
    #         #     print(output)
    #         #     print("<hr/>")
    # else:

    examine = [
        'chispar',  # missing chispa
        'querrían',  # missing querer
        'dijiste',  # missing decir
        'probado',  # missing probar , compare to abrumado
    ]

    # del wc.definitions['torva']
    #
    # output = wc.define('torva', '')
    info, links = wc.parser.fetch_with_links('torvo', 'Spanish')
    print("got info", info)
    print("got links", links)
    info, links = wc.parser.fetch_with_links('torvus', 'Latin')
    print("got info", info)
    print("got links", links)
    return
    print(html2.handle(output))

    i = 0
    for key in all_keys:
        wc.define(key, "")
        i += 1
        if (i % 10) == 0:
            print(f"{i} of {len(all_keys)}")
    wc.save()

    for word in ['torva']:
        del wc.definitions[word]
        output = '\n'.join(wc.define_full_list(6, word, lemma=None, source=''))
        print(output)
        print(html2.handle(output))
        print(wc.parser.PARTS_OF_SPEECH)
        print(wc.parser.RELATIONS)
        print(wc.parser.INCLUDED_ITEMS)


def dump_tokens(language: str, book_num: int, chapter: int):
    file_name = f'{language}/tokens_bk{book_num}_ch{chapter}.tsv'
    with open(file_name, 'r', newline='') as tsvfile:
        import csv
        tsv_file = csv.reader(tsvfile, delimiter="\t")
        i = 1
        for row in tsv_file:
            output = f"<h1>{i}. {row[0]}</h1>"
            output += f"<p>{row[1]}</p>"
            output += f"<p>{row[3]}</p>"
            output += f"<p>{row[4]}</p>"
            output += f"<p>{row[2]}</p>"
            output += f"<p>{row[5]}</p>"
            output += f"<p>{row[7]}</p>"
            output += "<hr>"
            if not WiktionaryCache.contains_reference_to_other_language(output):
                print(output)
            i += 1

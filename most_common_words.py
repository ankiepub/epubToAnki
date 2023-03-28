from typing import List, Dict

from spacy import Language as SpacyLanguage
import datetime

from csv_output import save_infos_to_csv
from deluxe_token_counter import DeluxeLemmaHit, get_deluxe_word_count, deluxe_hit_is_proper_noun
from lemma_lookup import LemmaLookup
from previously_imported_words import PreviouslyImportedWords


def get_deluxe_hit_roots(lemma_lookup: LemmaLookup, hit: DeluxeLemmaHit) -> List[Dict]:
    all_lemmas = lemma_lookup.get_lemmas(hit['lemma'])
    return all_lemmas


def output_most_common_new_words(language: str, number_of_words_to_find: int, nlp: SpacyLanguage):
    lemma_lookup = LemmaLookup.load(language)
    previously_imported_words = PreviouslyImportedWords.load_and_update(language, lemma_lookup)
    wc = get_deluxe_word_count(language)
    lbf = wc.get_lemmas_by_frequency()
    seen_roots = {}
    output_hits: List[DeluxeLemmaHit] = []
    i = 0
    while (len(output_hits) < number_of_words_to_find) and (i < len(lbf)):
        lemma = lbf[i]
        i += 1
        info = wc.get_hit_info(lemma)
        if not previously_imported_words.has_seen_info(info):
            lemma_roots = get_deluxe_hit_roots(lemma_lookup, info)
            if len(lemma_roots) > 0:
                already_seen = False
                root_set = {x['lemma']: True for x in lemma_roots}
                for root in root_set.keys():
                    if root in seen_roots:
                        already_seen = True
                    else:
                        seen_roots[root] = True
                    if previously_imported_words.has_seen_word_or_lemma(root):
                        already_seen = True
                if not already_seen:
                    output_hits.append(info)
                    print(i, lemma, info)
    save_infos_to_csv(language, output_hits,
                      f"{number_of_words_to_find}_most_common_words_{str(datetime.date.today())}", nlp)

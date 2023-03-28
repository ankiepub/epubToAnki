from by_chapter import create_chapter_words

from spacy import Language as SpacyLanguage

import spacy

from util import language_to_code

from most_common_words import output_most_common_new_words


def get_nlp(language: str) -> SpacyLanguage:
    language_code = language_to_code(language)
    spacy_pipeline = language_code + "_core_news_lg"
    try:
        nlp = spacy.load(spacy_pipeline)
        return nlp
    except ImportError:
        print(f"could not import spacy pipeline {spacy_pipeline}")
        print(f"refer to https://spacy.io/models/{language_code}")
        print(f"you may be install it like this: python -m spacy download {spacy_pipeline}")
        raise


def go():
    language = 'italian'
    nlp = get_nlp(language)

    create_by_chapters = False
    """
    IMPORTANT: The generated list of words needs to know what you have previously imported into Anki.
    This is determined by looking at CSV files in the already_imported directory.
    
    YOU MUST MOVE IMPORTED CSV FILES INTO already_imported AFTER IMPORTING
    """
    if create_by_chapters:
        """
        Create a list of words corresponding to chapters. 
        Only include words that appear more than once (or whatever frequency you set) 
        I found this to be useful when I was starting and needed a lof of help with vocab.
        """
        create_chapter_words(language, book_number=1, start_chapter=1, num_chapters=1, min_word_frequency=2, nlp=nlp)
    else:
        """
        Create a list of words ordered by frequency in a set of books.
        This was useful once my vocabulary was good enough to understand most of what I was reading.
        """
        output_most_common_new_words(language, number_of_words_to_find=21, nlp=nlp)
    return


if __name__ == '__main__':
    go()

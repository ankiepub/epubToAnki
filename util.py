import os
from typing import List

from bs4 import BeautifulSoup


def language_to_code(language: str) -> str:
    _language_to_code = {
        'english': 'en',
        'italian': 'it',
        'spanish': 'es'
    }
    language = language.lower()
    if language not in _language_to_code:
        raise Exception("_language_to_code missing language: " + language)
    return _language_to_code[language.lower()]


def timer_func(func):
    from time import time
    # This function shows the execution time of
    # the function object passed
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f'Function {func.__name__!r} executed in {(t2 - t1):.4f}s')
        return result

    return wrap_func


def is_text_chapter(item, language: str):
    """
    :param item: ebook chapter
    :param language: language of the chapter
    :return: whether this chapter appears to be text

    This function returns true for any chapter with at least 14,000 characters.
    This is very crude but it worked for me.
    """
    if len(item.get_body_content()) < 14000:
        return False
    return True


def chapter_to_str(chapter) -> str:
    soup = BeautifulSoup(chapter.get_body_content(), "html.parser")
    text = [para.get_text() for para in soup.find_all("p")]
    return " ".join(text)


def is_personal(part):
    if isinstance(part, list):
        for child in part:
            if is_personal(child):
                return True
    else:
        if part.find('person') > -1:
            return True
        elif part.find('singular') > -1:
            return True
        elif part.find('plural') > -1:
            return True
    return False


def part_to_str(part):
    if isinstance(part, list):
        return '/'.join([part_to_str(x) for x in part])
    else:
        return part


def unpersonal_parts(parts):
    try:
        return ' '.join([part_to_str(x) for x in parts if not is_personal(x)])
    except:
        print("error", parts)
        print([x for x in parts if not is_personal(x)])
        print([is_personal(x) for x in parts])
        print([is_personal(x) for x in parts[0]])
        raise


def get_books(language: str) -> List[str]:
    output = []
    root_path = os.path.join(language, 'books')
    for file in os.listdir(root_path):
        output.append(os.path.join(root_path, file))
    output.sort()
    return output


def get_biggest_word(sentence):
    words = sentence.split(' ')
    if len(words) < 2:
        return sentence
    biggest = words[0]
    for next_word in words:
        if len(next_word) > len(biggest):
            biggest = next_word
    return biggest


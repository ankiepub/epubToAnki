import re
from typing import Dict

from spacy import Language as SpacyLanguage

# def letters_to_tags(letters) -> []:
#     tags = []
#     for letters in letters:
#         tag_set = []
#         tags.append(tag_set)
#         prefix = ''
#         tag_set.append(''.join([f"<{prefix}{x}>" for x in letters]))
#         prefix = '/'
#         tag_set.append(''.join(reversed([f"<{prefix}{x}>" for x in letters])))
#     return tags
"""
Add emphasis logic:
When a token is FIRST found in a sentence, create a map from the sentence to the token (list).
When pulling the sentence for a token, we can pull the associated tokens. If there are too many tokens,
split by number of colors and choose whichever set our token appears in.

If the index of our token is X and there are N total tokens, with C colors, split the list into chunks of C:
0:C, C:2*C, etc.
start = X - (X % C)
end = min(len(tokens), start + C)



"""

def replace_token(doc, key, replacement, nlp: SpacyLanguage):
    from spacy.matcher import Matcher

    matcher = Matcher(nlp.vocab)
    matcher.add(key, [[{"TEXT": key}]])

    match_id, start, end = matcher(doc)[0]  # assuming only one match replacement
    return nlp.make_doc(doc[:start].text + f" {replacement} " + doc[end:].text)


_emphasis_tags = None
EMPHASIS_COLORS = ["e2eeff", "8fffef", "97ff78", "ffea9f", "ffd09f", "ffc7bc", "fbc7de"]


def colors_to_tags(colors) -> []:
    return [[f"<span style='background-color: #{x}'>", "</span>"] for x in colors]


def get_emphasis_tags():
    global _emphasis_tags, EMPHASIS_COLORS

    if _emphasis_tags is None:
        _emphasis_tags = colors_to_tags(EMPHASIS_COLORS)
    return _emphasis_tags


_emphasis_tag_regexes = None


def get_emphasis_tag_regexes() -> []:
    global _emphasis_tag_regexes, EMPHASIS_LETTERS
    if _emphasis_tag_regexes is None:
        _emphasis_tag_regexes = []
        for letters in EMPHASIS_LETTERS:
            tag_set = []
            _emphasis_tag_regexes.append(tag_set)
            tag_set.append(re.compile(' *'.join([' *'.join(f"<{x}>") for x in letters])))
            tag_set.append(re.compile(' *'.join([' *'.join(f"</{x}>") for x in reversed(letters)])))
    return _emphasis_tag_regexes


def add_token_emphasis_2(sentence_text: str, sentence_tokens: [str], token_text: str, nlp: SpacyLanguage) -> str:
    global EMPHASIS_COLORS
    max_highlights = len(EMPHASIS_COLORS)

    if len(sentence_tokens) <= max_highlights:
        highlight_tokens = {x for x in sentence_tokens}
    else:
        # too many tokens. Take the matching chunk
        x = sentence_tokens.index(token_text)
        start = x - (x % max_highlights)
        end = min(len(sentence_tokens), start + max_highlights)
        highlight_tokens = {x for x in sentence_tokens[start:end]}

    output, num_matches = _add_token_emphasis(sentence_text, highlight_tokens, nlp)
    if (num_matches > max_highlights) or (len(output) > 5000):
        output, num_matches = _add_token_emphasis(sentence_text, {token_text}, nlp)
    if len(output) > 5000:
        output = sentence_text[:5000]
    return output


def add_token_emphasis(text: str, token_text_set: {str}, token_text: str, chapter: int,
                       sentence_to_tokens: Dict[str, list], nlp: SpacyLanguage) -> str:
    global EMPHASIS_COLORS
    highlight_tokens = token_text_set
    max_highlights = len(EMPHASIS_COLORS)
    if True:
        sentence_tokens = sentence_to_tokens[text]
        if len(sentence_tokens) <= max_highlights:
            highlight_tokens = {x for x in sentence_tokens}
        else:
            # too many tokens. Take the matching chunk
            x = sentence_tokens.index(token_text)
            start = x - (x % max_highlights)
            end = min(len(sentence_tokens), start + max_highlights)
            highlight_tokens = {x for x in sentence_tokens[start:end]}

    output, num_matches = _add_token_emphasis(text, highlight_tokens, nlp)
    if (num_matches > max_highlights) or (len(output) > 5000):
        output, num_matches = _add_token_emphasis(text, {token_text}, nlp)
    if len(output) > 5000:
        output = text[:5000]
    return output


def _add_token_emphasis(text: str, token_text_set: {str}, nlp: SpacyLanguage) -> str:
    # import nltk
    # words = nltk.word_tokenize(raw_sentence)
    # print("add_token_emphasis", text)

    doc = nlp(text)
    matches = []
    seen = {}
    output = ""
    for sent in doc.sents:
        for token in sent:
            if token.text in token_text_set:
                if not token.text in seen:
                    matches.append(token.text)
                seen[token.text] = True

    output = ""

    match_to_color = {}
    tags = get_emphasis_tags()

    for i in range(0, len(matches)):
        # match_to_color[matches[i]] = f"<span style='background-color:#{colors[i % len(colors)]}'>{matches[i]}</span>"
        t = tags[i % len(tags)]
        match_to_color[matches[i]] = f"{t[0]}{matches[i]}{t[1]}"

    i_token = 0
    start = 0
    num_matches = 0
    for token in doc:
        if token.text in match_to_color:
            num_matches += 1
            if start < i_token:
                output += doc[start:i_token].text
            output += " " + match_to_color[token.text] + " "
            start = i_token + 1
        i_token += 1
    # now add the end
    output += doc[start:].text
    output = output.replace('  ', ' ')

    # doc = replace_token(doc, matches[i], f"<span style='background-color:#{colors[i % len(colors)]}'>{matches[i]}</span>", nlp)
    # print(" => ", output)
    return output, num_matches


def fix_emphasis_tags(text: str) -> str:
    # text = emphasis_letters_to_colors(text)
    return text


def emphasis_letters_to_colors(text: str) -> str:
    global EMPHASIS_LETTERS
    colors = ["e2eeff", "8fffef", "97ff78", "ffea9f", "ffd09f", "ffc7bc", "fbc7de"]
    tags = get_emphasis_tags()
    for i in range(0, len(tags)):
        i2 = len(tags) - (i + 1)
        tag = tags[i2]
        # find the tag and fix it
        color = colors[i2 % len(colors)]
        tag_letters = EMPHASIS_LETTERS[i2]

        start_regex, end_regex = get_emphasis_tag_regexes()[i2]
        start_color_tag = f"<span style='background-color:#{color}'>"
        end_color_tag = "</span>"
        text = re.sub(start_regex, start_color_tag, text, 0)
        text = re.sub(end_regex, end_color_tag, text, 0)

    return text

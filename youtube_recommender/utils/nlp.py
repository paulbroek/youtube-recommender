
def clean_up(text, nlp):
    """Step-1: clean up your text and generate list of words for each document.
    I recommend you go through an introductory tutorial on Spacy in this link.
    The content inside the cleanup function is designed for a specific action.
    I have provided two examples in the github repo"""

    removal = ["ADV", "PRON", "CCONJ", "PUNCT", "PART", "DET", "ADP", "SPACE"]
    text_out = []
    doc = nlp(text)
    for token in doc:
        if (
            not token.is_stop
            and token.is_alpha
            and len(token) > 2
            and token.pos_ not in removal
        ):
            lemma = token.lemma_
            text_out.append(lemma)

    return text_out

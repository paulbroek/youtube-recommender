""" 
extract topic models using spacy

help: https://medium.com/@soorajsubrahmannian/extracting-hidden-topics-in-a-corpus-55b2214fc17d
"""

import pandas as pd

import spacy
from gensim import models as gs_models
from gensim import corpora as gs_corpora

nlp = spacy.load("en_core_web_sm")
data = pd.read_feather("data/captions.feather")

NUM_TOPIC = 10


def clean_up(text):
    """ Step-1: clean up your text and generate list of words for each document. 
    I recommend you go through an introductory tutorial on Spacy in this link. 
    The content inside the cleanup function is designed for a specific action. 
    I have provided two examples in the github repo """

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


# datalist = data.text.apply(lambda x: clean_up(x))
datalist = data.text.map(clean_up)

# Step-2: Create a vocabulary for the lda model and
# convert our corpus into document-term matrix for Lda

dictionary = gs_corpora.Dictionary(datalist)
doc_term_matrix = [dictionary.doc2bow(doc) for doc in datalist]

# Step-3 : Define multicore lda model

Lda = gs_models.LdaMulticore
lda = Lda(
    doc_term_matrix,
    num_topics=NUM_TOPIC,
    id2word=dictionary,
    passes=20,
    chunksize=2000,
    random_state=3,
)

"""topic_modeling_gensim.py, extract topic models using spacy.

help: 
    https://medium.com/@soorajsubrahmannian/extracting-hidden-topics-in-a-corpus-55b2214fc17d

run:
    cd ~/repos/youtube-recommender
    ipy youtube-recommender/topic_modeling_gensim.py
"""

from functools import partial

import pandas as pd
import spacy
from gensim import corpora as gs_corpora
from gensim import models as gs_models
from settings import CAPTIONS_PATH, SPACY_MODEL
from utils.nlp import clean_up

# load spacy model and dataset
nlp = spacy.load(SPACY_MODEL)
data = pd.read_feather(CAPTIONS_PATH)

NUM_TOPIC = 10

clean_up = partial(clean_up, nlp=nlp)
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

# Step-4 : inspect topics

# lda.show_topics(0)
# lda.show_topics(1)

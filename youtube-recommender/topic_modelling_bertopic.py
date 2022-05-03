"""
Based on:
    https://www.holisticseo.digital/python-seo/topic-modeling/

Run:
    conda activate py39
    cd ~/repos/youtube-recommender/youtube-recommender
    ipy topic_modelling_bertopic.py

Caution: 
    Bertopic doesn't work when number of documents is too low, see:
    https://github.com/MaartenGr/BERTopic/issues/97

    My solution is to concat duplicate lists together, so there are more docs to train on
"""

import pandas as pd

# from sklearn.datasets import fetch_20newsgroups
from bertopic import BERTopic
from settings import CAPTIONS_PATH

data = pd.read_feather(CAPTIONS_PATH)
docs = data["text"].to_list()

# bertopic only works with many documents, not a small number
if len(docs) < 20:
    dupls = 5
    to_copy = docs.copy()
    for i in range(dupls):
        docs += to_copy

topic_model = BERTopic()

# docs = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']
topics, probs = topic_model.fit_transform(docs)

# inspect a topic
# topic_model.get_topic(0)

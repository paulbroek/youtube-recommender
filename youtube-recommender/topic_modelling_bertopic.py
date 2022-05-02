"""
inspired by:
    https://www.holisticseo.digital/python-seo/topic-modeling/

Run:
    cd ~/repos/youtube-recommender/youtube-recommender
    ipy topic_modelling_bertopic.py
"""

import pandas as pd
# from sklearn.datasets import fetch_20newsgroups
from bertopic import BERTopic

data = pd.read_feather("data/captions.feather")
docs = data["text"].to_list()

# bertopic only works with many documents, not a small number
if len(docs) < 300:
    dupls = 10
    to_copy = docs.copy()
    for i in range(dupls):
        docs += to_copy

topic_model = BERTopic()

# docs = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']
topics, probs = topic_model.fit_transform(docs)

"""topic_modelling_bertopic.py.

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

Todo:
    Create video summary dataset from postgres, and extract topics from that
"""

import pandas as pd
# from sklearn.datasets import fetch_20newsgroups
from bertopic import BERTopic  # type: ignore[import]
from youtube_recommender.settings import CAPTIONS_PATH, EDUCATIONAL_VIDEOS_PATH

data = pd.read_feather(EDUCATIONAL_VIDEOS_PATH)
# data = pd.read_feather(CAPTIONS_PATH)
# docs = data["text"].to_list()
docs = data["description"].to_list()

topic_model = BERTopic()

# docs = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']
topics, probs = topic_model.fit_transform(docs)

# inspect a topic
# topic_model.get_topic(0)

# show topics with probabilities in dataframe
info = topic_model.get_topic_info()[1:].reset_index(drop=True).copy()
assert info.Topic.is_monotonic_increasing
# set_index("Topic", drop=False)
# .sort_values("Topic")


def similar_topics_to_search_term(
    model: BERTopic, info: pd.DataFrame, search_term: str, top_n=5
) -> pd.DataFrame:
    """Find and sort by relevance topics with a certain word.

    Usage:
        info = topic_model.get_topic_info()[1:].reset_index(drop=True).copy()
        most_similar = similar_topics_to_search_term(topic_model, info, "cloud", top_n=5)
    """
    topic_dict = dict(zip(*model.find_topics(search_term, top_n=top_n)))
    ixs = list(topic_dict.keys())
    df: pd.DataFrame = info.iloc[ixs].copy()
    df["Similarity"] = df.Topic.map(topic_dict)

    return df

most_similar = similar_topics_to_search_term(topic_model, info, "cloud", top_n=5)

# todo: extract the channel names that cover certain topics most

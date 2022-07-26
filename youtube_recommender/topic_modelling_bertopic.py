"""topic_modelling_bertopic.py.

Based on:
    https://www.holisticseo.digital/python-seo/topic-modeling/

Run:
    conda activate py39
    cd ~/repos/youtube-recommender/youtube-recommender
    ipy topic_modelling_bertopic.py -i -- -s

    # load existing model
    ipy topic_modelling_bertopic.py -i -- -l

Caution: 
    
    - Bertopic doesn't work when number of documents is too low, see:
        https://github.com/MaartenGr/BERTopic/issues/97

        My solution is to concat duplicate lists together, so there are more docs to train on

    - use topic_model.reduce_topics to reduce the number of topics. Like:
        new_topics, new_probs = topic_model.reduce_topics(docs, topics, probs, nr_topics=30)


Todo:
    Create video summary dataset from postgres, and extract topics from that
"""

import argparse
import logging

import pandas as pd
# from sklearn.datasets import fetch_20newsgroups
from bertopic import BERTopic  # type: ignore[import]
from path import Path
from rarc_utils.log import setup_logger
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import EDUCATIONAL_VIDEOS_PATH

# CAPTIONS_PATH

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

MODEL_PATH = "export/educational_video_descriptions.model"
TOPICS_PATH = Path("export/educational_video_descriptions.feather")


def similar_topics_to_search_term(
    model: BERTopic, info: pd.DataFrame, search_term: str, top_n=5
) -> pd.DataFrame:
    """Find and sort by similar topics to a certain word.

    Usage:
        info = topic_model.get_topic_info()[1:].reset_index(drop=True)
        most_similar = similar_topics_to_search_term(topic_model, info, "cloud", top_n=5)
    """
    topic_dict = dict(zip(*model.find_topics(search_term, top_n=top_n)))
    ixs = list(topic_dict.keys())
    df: pd.DataFrame = info.iloc[ixs].copy()
    df["Similarity"] = df.Topic.map(topic_dict)

    return df


def topic_presence_by_channel(
    model: BERTopic, info: pd.DataFrame, topic_id: int, top_n=5
) -> pd.DataFrame:
    """Find which channels cover some topics mostly."""

    pass


parser = argparse.ArgumentParser(
    description="topic_modelling_bertopic optional parameters"
)
parser.add_argument(
    "-l",
    "--load_model",
    action="store_true",
    default=False,
    help="Load bertopic model",
)
parser.add_argument(
    "-s",
    "--save_model",
    action="store_true",
    default=False,
    help="Save bertopic model",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # docs = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']
    data = pd.read_feather(EDUCATIONAL_VIDEOS_PATH)
    # data = pd.read_feather(CAPTIONS_PATH)
    # docs = data["text"].to_list()
    docs = data["description"].to_list()

    if args.load_model:
        topic_model = BERTopic.load(MODEL_PATH)
        topics, probs = im.load_topics(TOPICS_PATH)
    else:
        topic_model = BERTopic()
        topics, probs = topic_model.fit_transform(docs)

    # inspect a topic
    # topic_model.get_topic(0)

    # show topics with probabilities in dataframe
    info = topic_model.get_topic_info()[1:].sort_values("Topic").reset_index(drop=True)
    assert info.Topic.is_monotonic_increasing

    most_similar = similar_topics_to_search_term(topic_model, info, "cloud", top_n=5)

    # todo: extract the channel names that cover certain topics most

    # todo: use dataset hash to determine if data changed, add a different model id to the file path
    if args.save_model and not args.load_model:
        topic_model.save(MODEL_PATH)
        im.save_topics(topics, probs, TOPICS_PATH)

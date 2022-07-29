"""bertopic_model.py.

Based on:
    https://www.holisticseo.digital/python-seo/topic-modeling/
    docs: https://maartengr.github.io/BERTopic/index.html#overview

Run:
    conda activate py39
    cd ~/repos/youtube-recommender/youtube-recommender/topic_modeling
    # train model and save to feather
    ipy bertopic_model.py -i -- -s

    # load existing model, topics and probabilities
    ipy bertopic_model.py -i -- -l

Caution: 
    - Bertopic doesn't work when number of documents is too low, see:
        https://github.com/MaartenGr/BERTopic/issues/97

        So use larger datasets

    - use topic_model.reduce_topics to reduce the number of topics. Like:
        new_topics, new_probs = topic_model.reduce_topics(docs, topics, probs, nr_topics=30)

    - other important methods:
        topic_model.set_topic_labels(my_custom_labels)   set custom topic labels
        topic_model.get_representative_docs()

Todo:
    Create video summary dataset from postgres, and extract topics from that
"""

import argparse
import logging

import pandas as pd
# from sklearn.datasets import fetch_20newsgroups
from bertopic import BERTopic  # type: ignore[import]
from rarc_utils.log import setup_logger
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (EDUCATIONAL_VIDEOS_PATH, MODEL_PATH,
                                          TOPICS_PATH)
from youtube_recommender.topic_modeling.methods import (similar_topics_to_word,
                                                        topic_presence_by)

# CAPTIONS_PATH

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

parser = argparse.ArgumentParser(
    description="topic_modeling/bertopic_model optional parameters"
)
parser.add_argument(
    "-l",
    "--load_model",
    action="store_true",
    default=False,
    help="Load bertopic model, topics and probabilities",
)
parser.add_argument(
    "-s",
    "--save_model",
    action="store_true",
    default=False,
    help="Save bertopic model, topics and probabilities",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # docs = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']
    data = pd.read_feather(EDUCATIONAL_VIDEOS_PATH)
    # data = pd.read_feather(CAPTIONS_PATH)
    # docs = data["text"].to_list()
    docs = data["description"].to_list()
    doc_to_channel_id = dict(zip(*data[["description", "channel_id"]].values.T))
    doc_to_channel_name = dict(zip(*data[["description", "channel_name"]].values.T))

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
    logger.info(
        f"this model uses {len(info):,} topics, derived from {len(docs):,} documents"
    )

    most_similar = similar_topics_to_word(topic_model, info, "cloud", top_n=5)

    # extract the channel names that cover certain topics most
    df = topic_presence_by(topic_model, info, doc_to_channel_name, by="channel")
    # doc_to_channel_id

    # todo: use dataset hash to determine if data changed, add a different model id to the file path
    if args.save_model and not args.load_model:
        topic_model.save(MODEL_PATH)
        im.save_topics(topics, probs, TOPICS_PATH)

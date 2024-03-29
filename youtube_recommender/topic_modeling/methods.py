import logging
from typing import Any, Dict

import pandas as pd
from bertopic import BERTopic

logger = logging.getLogger(__name__)


def similar_topics_to_word(
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


def topic_presence_by(
    model: BERTopic,
    info: pd.DataFrame,
    doc_to: Dict[str, Any],
    by="channel",
) -> pd.DataFrame:
    """Find which channels cover a topic mostly.

    Usage:
        df = topic_presence_by(topic_model, info, doc_to=doc_to_channel_name, by="channel")
    """
    df = info.copy()
    df["representative_docs"] = df.Topic.map(model.get_representative_docs)
    df["nrepresentative_docs"] = df["representative_docs"].map(len)
    # returns always 3 docs. not enough?
    df[f"representative_{by}s"] = df["representative_docs"].map(
        lambda x: [doc_to.get(y, None) for y in x]
    )
    # doc_to_channel_id

    return df

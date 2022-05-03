""" data_methods.py

    methods related to working with dataframes
"""

from operator import itemgetter
import logging
from yapic import json

import pandas as pd
import langid

logger = logging.getLogger(__name__)

LANGUAGE_CL = "language_cl"
LANGUAGE_CODE = "language_code"


def extract_video_id(df: pd.DataFrame, urlCol="Video URL") -> pd.DataFrame:
    """extracts YouTube's video_id from plain URL
    example: https://www.youtube.com/watch?v=t0OX4jbFwvM --> t0OX4jbFwvM
    """
    assert urlCol in df.columns
    df = df.copy()
    df["video_id"] = df[urlCol].str.rsplit("?v=", n=1).str[1]

    return df


def classify_language(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """classify the language of a pandas column"""

    assert column in df.columns, f"{column=} not in {df.columns=}"

    df = df.copy()

    df[LANGUAGE_CL] = df[column].map(langid.classify)
    df[LANGUAGE_CODE] = df[LANGUAGE_CL].map(itemgetter(0))
    df[LANGUAGE_CL] = df[LANGUAGE_CL].map(json.dumps)  # makes it serializable

    return df


def keep_language(df: pd.DataFrame, lang_code: str) -> pd.DataFrame:
    """keep only rows of language `lang_code`"""

    # `classify_language` should run before this method
    assert LANGUAGE_CL in df.columns
    assert LANGUAGE_CODE in df.columns
    assert lang_code in df[LANGUAGE_CODE].to_list()

    rows_before = len(df)
    df = df[df.language_code == "en"].reset_index(drop=True)
    rows_after = len(df)

    logger.info(
        f"keeping {rows_after:,} rows. dismissed {rows_before - rows_after} non-{lang_code} rows"
    )

    return df


def merge_captions_with_videos(
    df_captions: pd.DataFrame,
    df_videos: pd.DataFrame,
    dropCols=("language_cl", "language_code", "Video URL"),
) -> pd.DataFrame:

    vdf = df_videos.drop(list(dropCols), axis=1)

    # join on `video_id`
    bdf = pd.merge(df_captions, vdf, left_on="video_id", right_on="video_id")

    logger.info("merged df_captions with df_videos")

    return bdf

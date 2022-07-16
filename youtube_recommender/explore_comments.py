r"""explore_comments.py.

Explore the comments dataset using NLP, uses libraries spaCy and SpacyTextBlob

    # load from feather
    ipy explore_comments.py -i -- --load_feather

    # load from DB
    ipy explore_comments.py -i -- --load_db --video_ids vLnPwxZdW4Y SPTfmiYiuok --dryrun
    ipy explore_comments.py -i -- --load_db --video_ids vLnPwxZdW4Y SPTfmiYiuok
    ipy explore_comments.py -i -- --load_db --video_ids vLnPwxZdW4Y SPTfmiYiuok --save_pickle

Datasets explained:
    comments.feather    holds parsed rows. rows that can be parsed to SQLAlchemy objects
    comments.pickle     holds rows with (comment_id, Doc), should be joined with SQL / feather dataset to reconstruct dataset before saving
"""

import argparse
import asyncio
import logging
import sys
from typing import List

import pandas as pd
import spacy
from rarc_utils.decorators import items_per_sec
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session
from spacytextblob.spacytextblob import SpacyTextBlob  # type: ignore[import]
from youtube_recommender.db.helpers import get_comments_by_video_ids
from youtube_recommender.db.models import psql
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (COMMENTS_FEATHER_FILE,
                                          COMMENTS_PICKLE_FILE)

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

async_session = get_async_session(psql)

loop = asyncio.get_event_loop()
NLP_COMMENT = "nlp_comment"


@items_per_sec
def comments_by_vids(video_ids: List[str]):
    """Get comments by video_ids wrapper."""
    logger.info(f"get rows from DB..")
    return loop.run_until_complete(
        get_comments_by_video_ids(async_session, args.video_ids)
    )



parser = argparse.ArgumentParser(description="Define get_coments parameters")
parser.add_argument(
    "--video_ids",
    default=[],
    nargs="*",
    help="video_id to download comments for, if channel_id was not passed",
)
parser.add_argument(
    "--max",
    type=int,
    default=0,
    help="max videos to get comments for",
)
parser.add_argument(
    "--skip",
    type=int,
    default=0,
    help="videos to skip",
)
parser.add_argument(
    "--load_db",
    action="store_true",
    default=False,
    help="load dataset from db",
)
parser.add_argument(
    "--load_feather",
    action="store_true",
    default=False,
    help="load .feather dataset from disk",
)
parser.add_argument(
    "--load_pickle",
    action="store_true",
    default=False,
    help="load NLP dataset from .pickle file",
)
parser.add_argument(
    "--save_pickle",
    action="store_true",
    default=False,
    help="save NLP dataset to .pickle file",
)
parser.add_argument(
    "--dryrun",
    action="store_true",
    default=False,
    help="only import modules",
)


if __name__ == "__main__":
    args = parser.parse_args()

    if args.load_pickle:
        ndf = im.load_pickle(COMMENTS_PICKLE_FILE, NLP_COMMENT)

        # todo: merge with sql dataset

        sys.exit()

    LOADED_DF = False
    if args.load_db:
        assert args.video_ids, f"please pass video_ids"
        items = comments_by_vids(args.video_ids)

        df = pd.DataFrame(items)
        # df["hash_id"] = df.id.map(hash)
        # df = df.drop(["id", "updated", "created", "channel_id"], axis=1)
        df = df.drop(["updated", "created", "channel_id"], axis=1)
        LOADED_DF = True

    elif args.load_feather:
        df = im.load_feather(COMMENTS_FEATHER_FILE, what="comment")
        dropCols = [
            "time_parsed_float",
            "author_len",
            "votes_isdigit",
            "paid",
            "heart",
            "photo",
            "index",
            "time",
        ]
        df = df.drop(columns=dropCols).rename(columns={"cid": "id"})
        LOADED_DF = True

    assert LOADED_DF, f"please select a load method"

    if args.dryrun:
        sys.exit()

    nlp_without_textblob = spacy.load("en_core_web_md")
    nlp = spacy.load("en_core_web_md")
    # Add SpacyTextBlob to the pipeline
    nlp.add_pipe("spacytextblob")

    # slow, so use a subset of rows
    ndf = df
    # ndf = df.head(10_000).copy()
    # cannot serialize textblob objects..
    ndf["doc"] = list(nlp.pipe(ndf["text"]))
    # ndf["doc"] = list(nlp_without_textblob.pipe(ndf["text"], n_process=10))

    # only save Id and Doc to pickle, so they can be joined later for quick loading
    if args.save_pickle:
        im.save_pickle(ndf[["id", "doc"]], COMMENTS_PICKLE_FILE, NLP_COMMENT)

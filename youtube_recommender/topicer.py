"""topicer.py, CLI tool to extract topics from youtube videos.

@author: paulbroek
"""

import argparse
import asyncio
import logging
import sys
from typing import Any, Dict, List

import uvloop
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, get_session

from .caption_finder import (
    adownload_captions,
    captions_to_df,
    save_feather,
    select_video_ids,
)
from .data_methods import data_methods as dm
from .db.helpers import get_captions_by_video_ids
from .db.models import psql
from .settings import CAPTIONS_PATH, VIDEOS_PATH
from .video_finder import load_feather

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, fmt=log_fmt
)  # DEBUG

parser = argparse.ArgumentParser(description="Defining parameters")

parser.add_argument(
    "video_ids",
    type=str,
    nargs="*",
    help="The YouTube videos to extract captions from. Can be multiple.",
)
parser.add_argument(
    "--from_feather",
    action="store_true",
    default=False,
    help=f"Import video ids from `{VIDEOS_PATH.as_posix()}`, created in main.py. ignores any manually passed video_ids",
)
parser.add_argument(
    "-n",
    type=int,
    default=0,
    help=f"select first `n` rows from feather file",
)
parser.add_argument(
    "--dryrun",
    action="store_true",
    default=False,
    help="only load data, do not download captions",
)
parser.add_argument(
    "--merge_with_videos",
    action="store_true",
    default=False,
    help="merge resulting captions dataset with videos metadata",
)
parser.add_argument(
    "-s",
    "--save_captions",
    action="store_true",
    default=False,
    help=f"Save captions to `{CAPTIONS_PATH.as_posix()}`",
)
parser.add_argument(
    "-p",
    "--push_db",
    action="store_true",
    default=False,
    help="push Video, Channel and Caption rows to PostgreSQL`",
)


if __name__ == "__main__":

    args = parser.parse_args()

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()

    async_session = get_async_session(psql)
    psession = get_session(psql)()

    # load videos file and select video_ids
    if args.from_feather:
        vdf = load_feather(VIDEOS_PATH)
        video_ids = select_video_ids(vdf, n=args.n)

    else:
        video_ids = args.video_ids

    if args.dryrun:
        sys.exit()

    # get captions from cache
    existing_captions = loop.run_until_complete(
        get_captions_by_video_ids(async_session, video_ids)
    )

    logger.info(f"{len(existing_captions)=} {existing_captions=}")

    # download captions
    # captions = download_captions(video_ids) # blocking way
    captions_list: List[Dict[str, Any]] = loop.run_until_complete(
        adownload_captions(video_ids)
    )
    df = captions_to_df(captions_list)

    if args.merge_with_videos:
        df = dm.merge_captions_with_videos(df, vdf)

    if args.save_captions:
        save_feather(df, CAPTIONS_PATH)

    if args.push_db:
        # dm.push_captions(df, vdf, async_session)

        captions = loop.run_until_complete(dm.push_captions(df, vdf, async_session))

"""topicer.py, CLI tool to extract topics from youtube videos.

@author: paulbroek
"""

import argparse
import asyncio
import logging
import sys
from typing import Any, Dict, List

import pyperclip
import uvloop
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, get_session

from ..caption_finder import (adownload_captions, captions_to_df, save_feather,
                              select_video_ids)
from ..data_methods import data_methods as dm
from ..db.helpers import get_captions_by_vids
from ..db.models import Caption, psql
from ..settings import CAPTIONS_PATH, VIDEOS_PATH
from ..video_finder import load_feather

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)  # DEBUG

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()

async_session = get_async_session(psql)
psession = get_session(psql)()

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
    "-f",
    "--force",
    action="store_true",
    default=False,
    help="force to download captions, do not use cache",
)
parser.add_argument(
    "--merge_with_videos",
    action="store_true",
    default=False,
    help="merge resulting captions dataset with videos metadata",
)
parser.add_argument(
    "--with_start_times",
    action="store_true",
    default=False,
    help="include start_times in the output caption string",
)
parser.add_argument(
    "-s",
    "--save_captions",
    action="store_true",
    default=False,
    help=f"Save captions to `{CAPTIONS_PATH.as_posix()}`",
)
parser.add_argument(
    "-c",
    "--to_clipboard",
    action="store_true",
    default=False,
    help="Save captions to clipboard",
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
    exiting = False

    # load videos df and select video_ids
    if args.from_feather:
        vdf = load_feather(VIDEOS_PATH)
        video_ids = select_video_ids(vdf, n=args.n)

    else:
        video_ids = args.video_ids

    if args.dryrun or (args.from_feather and vdf.empty):
        sys.exit()

    # check cache for existing captions
    if not args.force:
        existing_captions = loop.run_until_complete(
            get_captions_by_vids(async_session, video_ids)
        )
        if len(existing_captions) > 0:
            existing_video_ids = set(c.video.id for c in existing_captions)

            # filter video_ids based on those existing_captions
            video_ids = list(set(video_ids) - existing_video_ids)

    # download captions
    # captions = download_captions(video_ids) # blocking way
    captions_list: List[Dict[str, Any]] = loop.run_until_complete(
        adownload_captions(video_ids, withStartTimes=args.with_start_times)
    )
    df = captions_to_df(captions_list)

    if df.empty:
        logger.info("nothing to do")
        exiting = True
        # sys.exit()  # deletes variables, not what you want

    if not exiting:
        if args.merge_with_videos:
            df = dm.merge_captions_with_videos(df, vdf)

        if args.save_captions:
            save_feather(df, CAPTIONS_PATH)

        if args.to_clipboard:
            if len(df) > 1:
                logger.warning("data contains more than one row, only printing first row")
            pyperclip.copy(df.text[0])

        if args.push_db:
            captions: Dict[str, Caption] = loop.run_until_complete(
                dm.push_captions(df, vdf, async_session, returnExisting=True)
            )

""" topicer.py
CLI tool to extract topics from youtube videos 
@author: paulbroek
"""

import argparse
import sys
import logging
import asyncio
import uvloop

from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, get_session #, aget_or_create_many

import caption_finder as cf
import data_methods as dm
from db.models import Video, Channel, psql
from db.helpers import create_many_items
from settings import VIDEOS_PATH, CAPTIONS_PATH

log_fmt = "%(asctime)s - %(module)-14s - %(lineno)-4s - %(funcName)-18s - %(levelname)-7s - %(message)s"  # name
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
    help="push Video, Channel and Caption rows to postgres / redis`",
)

args = parser.parse_args()

if __name__ == "__main__":

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()

    async_session = get_async_session(psql)
    psession = get_session(psql)()

    # parse video_ids
    if args.from_feather:

        vdf = cf.load_feather(VIDEOS_PATH)
        video_ids = vdf.video_id.to_list()
        if args.n > 0:
            video_ids = video_ids[: args.n]

        logger.info(f"loaded {len(video_ids):,} video metadata rows")
    else:
        video_ids = args.video_ids

    if args.dryrun:
        sys.exit()

    # download captions
    # captions = cf.download_captions(video_ids) # blocking way
    captions = loop.run_until_complete(cf.adownload_captions(video_ids))
    df = cf.captions_to_df(captions)

    if args.merge_with_videos:
        df = dm.merge_captions_with_videos(df, vdf)

    if args.save_captions:

        df.to_feather(CAPTIONS_PATH)
        logger.info(f"saved {len(df):,} captions to {CAPTIONS_PATH.as_posix()}")

    if args.push_db:

        # get list of dicts for Channel and Video
        channel_recs = (
            vdf.rename(
                columns={
                    "channel_id": "id",
                    "Channel Name": "name",
                    "Num_subscribers": "num_subscribers",
                }
            )[["id", "name", "num_subscribers"]]
            .assign(index=vdf["channel_id"])
            .set_index('index')
            # .drop_duplicates(subset=["id"])
            .drop_duplicates()
            .to_dict("index")
        )

        # create channels from same dataset

        channels_dict = loop.run_until_complete(
            create_many_items(async_session, Channel, channel_recs, nameAttr="id", returnExisting=True)
        )

        # map the new channels into vdf
        vdf["channel"] = vdf["channel_id"].map(channels_dict)

        video_recs = (
            vdf.rename(
                columns={
                    "video_id": "id",
                    "Title": "title",
                    "Description": "description",
                    "Views": "views",
                    "Custom_Score": "custom_score",
                }
            )[["id", "title", "description", "views", "custom_score", "channel_id", "channel"]]
            .assign(index=vdf["video_id"])
            .set_index('index')
            .drop_duplicates()
            .to_dict("index")
        )

        videos_dict = loop.run_until_complete(
            create_many_items(async_session, Video, video_recs, nameAttr="id", returnExisting=False)
        )

        # todo: save captions to redis, or what other database?

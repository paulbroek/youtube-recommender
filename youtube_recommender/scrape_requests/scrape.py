"""scrape.py, scraping Channel, Video, Comment data automatically using GRPC

example usage:
    ipy pytube_scrape.py -i -- --ncore 12 -sp -n 50 --channel_url https://www.youtube.com/channel/UC8butISFwT-Wl7EV0hUK0BQ
"""

import argparse
import asyncio
import logging
import sys
from http.client import RemoteDisconnected
from multiprocessing import Pool
from time import time
from typing import Any, Dict, List, Set

import pandas as pd
from pytube import Channel as pytube_channel  # type: ignore[import]
from pytube import YouTube  # type: ignore[import]
# from pytube import Playlist, Search
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, load_config
from youtube_recommender import config as config_dir
from youtube_recommender.data_methods import data_methods as dm
# from youtube_recommender.db.helpers import (
#     get_keyword_association_rows_by_ids, get_video_ids_by_ids)
from youtube_recommender.db.helpers import get_video_ids_by_channel_ids
from youtube_recommender.settings import (CHANNEL_FIELDS, PYTUBE_VIDEOS_PATH,
                                          VIDEO_FIELDS)
from youtube_recommender.video_finder import load_feather, save_feather

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)  # DEBUG


loop = asyncio.get_event_loop()

parser = argparse.ArgumentParser(description="Defining pytube_scrape parameters")
parser.add_argument(
    "--cfg_file",
    type=str,
    default="postgres.cfg",
    help="choose a configuration file",
)
parser.add_argument(
    "--channel_url",
    type=str,
    help="channel url to fetch video metadatas from",
)
parser.add_argument(
    "--skip",
    default=0,
    help="Skip first N items",
)
parser.add_argument(
    "-n",
    "--nitems",
    default=30,
    help="Max items to keep from channel",
)
parser.add_argument(
    "--only_new",
    action="store_true",
    default=False,
    help="only scrape video ids that are not seen in db",
)
parser.add_argument(
    "-p",
    "--push_db",
    action="store_true",
    default=False,
    help="push queryResult and Video rows to PostgreSQL`",
)
parser.add_argument(
    "--dryrun",
    action="store_true",
    default=False,
    help="only import modules",
)

if __name__ == "__main__":
    args = parser.parse_args()
    if args.dryrun:
        sys.exit()

    psql = load_config(
        db_name="youtube",
        cfg_file=args.cfg_file,
        config_dir=config_dir,
        starts_with=True,
    )
    async_session = get_async_session(psql)

    assert isinstance(args.channel_url, str), "pass url as string"

    nskip: int = int(args.skip)

    # todo: get scrapeJobs from db
    vurls: pytube_channel = pytube_channel(args.channel_url)

    # slow call to urls.len?
    # logger.info(f"this channel has {len(vurls):,} videos")
    last_item: int = nskip + nitems
    if nskip > len(vurls):
        raise IndexError(f"{nskip=:,} should be smaller than {len(vurls)=:,}")

    last_item = min(last_item, len(vurls))
    sel_vurls: List[str] = vurls[nskip:last_item]

    # filter vurls based on video_ids in db
    if args.only_new:
        existing_video_ids = loop.run_until_complete(
            get_video_ids_by_channel_ids(async_session, [vurls.channel_id])
        )
        vurl_df = pd.DataFrame(dict(url=vurls))
        vurl_df["video_id"] = vurl_df.url.str.split(r"\?v=").map(lambda x: x[-1])
        new_vurls = vurl_df[~vurl_df.video_id.isin(existing_video_ids)]

        if new_vurls.empty:
            logger.warning(f"nothing to do for channel={args.channel_url}")
            sys.exit()
        else:
            sel_vurls = new_vurls.url.to_list()

        vres = mp_extract_videos(sel_vurls, nprocess=ncore)
        cres = mp_extract_channels(vres, nprocess=ncore)
        vdf = pd.DataFrame(vres)
        cdf = pd.DataFrame(cres)

        # todo: get num_subscribers through beautifulsoup or YouTube API
        cdf["num_subscribers"] = None
        vdf["custom_score"] = None

        # combine video and channel data into one dataset
        df = pd.merge(vdf, cdf, on=["channel_id"])

        assert not df.empty

        if args.save:
            save_feather(df, PYTUBE_VIDEOS_PATH)

    # push keywords, channels and videos to db
    if args.push_db:
        df, cdf = dm.extract_chapters(df)
        datad = loop.run_until_complete(dm.push_videos(df, async_session))

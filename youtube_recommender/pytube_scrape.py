"""pytube_scrape.py, scraping metadata of videos through pytube.

pytube docs: 
    https://readthedocs.org/projects/python-pytube/downloads/pdf/stable/

example usage:
    ipy pytube_scrape.py -i -- --ncore 12 -sp -n 50 --channel_url https://www.youtube.com/channel/UC8butISFwT-Wl7EV0hUK0BQ

"""

import argparse
import asyncio
import logging
import sys
from multiprocessing import Pool
from time import time
from typing import Any, Dict, List

import pandas as pd
from pytube import Channel, YouTube  # type: ignore[import]
# from pytube import Playlist, Search
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session
from youtube_recommender.data_methods import data_methods as dm
# from youtube_recommender.db.helpers import (
#     get_keyword_association_rows_by_ids, get_video_ids_by_ids)
from youtube_recommender.db.models import psql
from youtube_recommender.settings import PYTUBE_VIDEOS_PATH
from youtube_recommender.video_finder import load_feather, save_feather

async_session = get_async_session(psql)

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)  # DEBUG

VIDEO_FIELDS = (
    "title",
    "channel_id",
    "channel_url",
    "description",
    "keywords",
    "length",
    "rating",
    "publish_date",
    "views",
    "video_id",
)

CHANNEL_FIELDS = (
    "title",
    "channel_id",
)


def extract_video_fields(
    url: str,
    fields=VIDEO_FIELDS,
) -> Dict[str, Any]:
    """Extract selected fields from YouTube object."""
    assert isinstance(url, str)

    yt_obj = YouTube(url)
    res = {}
    # slow?
    for field in fields:
        res[field] = getattr(yt_obj, field)

    return res


def extract_channel_fields(
    url: str,
    fields=CHANNEL_FIELDS,
) -> Dict[str, Any]:
    """Extract selected fields from Channel object."""
    assert isinstance(url, str)

    chan = Channel(url)
    res = {}
    # slow?
    for field in fields:
        try:
            if field == "title":
                res["channel_name"] = chan.initial_data["metadata"][
                    "channelMetadataRenderer"
                ]["title"]
            else:
                res[field] = getattr(chan, field)
        except AttributeError:
            logger.error(f"cannot get {field=}")

    return res


def extract_multiple_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """Extract metadata from multiple urls. Using slow for loop."""
    res = []
    t0 = time()
    # slow?
    for url in urls:
        yt = YouTube(url)
        res.append(extract_video_fields(yt))

    elapsed = time() - t0
    download_rate = len(res) / elapsed
    logger.info(
        f"got {len(res):,} items in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )
    return res


def mp_extract_videos(urls: List[str], nprocess: int) -> List[Dict[str, Any]]:
    """Multiprocessing extract metadata from multiple urls."""
    t0 = time()
    with Pool(processes=nprocess) as pool:
        res = pool.map(extract_video_fields, urls)

    elapsed = time() - t0
    download_rate = len(res) / elapsed
    logger.info(
        f"got {len(res):,} items in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )

    return res


def mp_extract_channels(res: List[Dict[str, Any]], nprocess: int):
    """Extract metadata for multiple videos + channel names."""
    # get unique channels
    channel_urls = set(r["channel_url"] for r in res)

    t0 = time()
    with Pool(processes=nprocess) as pool:
        res = pool.map(extract_channel_fields, channel_urls)

    elapsed = time() - t0
    download_rate = len(res) / elapsed
    logger.info(
        f"got {len(res):,} channel metadatas in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )

    return res


loop = asyncio.get_event_loop()
# d = extract_video_fields(url)
# dd = extract_multiple_urls(urls)
# dd = loop.run_until_complete(aextract_multiple_urls(urls[:10]))

# search
# res = Search("algo trading")
# res.results

parser = argparse.ArgumentParser(description="Defining pytube_scrape parameters")
parser.add_argument(
    "--ncore",
    default=8,
    help="Max cores to use for multiprocessing",
)
parser.add_argument(
    "--channel_url",
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
    "--load",
    action="store_true",
    default=False,
    help="Only load previous dataset",
)
parser.add_argument(
    "-s",
    "--save",
    action="store_true",
    default=False,
    help="Save pickled videos df to feather",
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

    assert isinstance(args.channel_url, str), "pass url as string"

    nskip = int(args.skip)
    nitems = int(args.nitems)
    ncore = int(args.ncore)

    # url = "https://www.youtube.com/watch?v=K4xMBckipWM"
    # yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
    # yt = YouTube(url)

    # get list of videos by Channel
    # channel_url = "https://www.youtube.com/c/DaltonMabery"
    # channel_url = "https://www.youtube.com/channel/UCPZUQqtVDmcjm4NY5FkzqLA"
    # urls = Channel(channel_url)

    # todo: load cannot be used to push items, since object relation to db is lost
    if args.load:
        df = load_feather(PYTUBE_VIDEOS_PATH)

    else:
        vurls = Channel(args.channel_url)

        # slow call to urls.len?
        # logger.info(f"this channel has {len(vurls):,} videos")
        last_item = nskip + nitems
        if nskip > len(vurls):
            raise IndexError(f"{nskip=:,} should be smaller than {len(vurls)=:,}")

        last_item = min(last_item, len(vurls))

        sel_vurls = vurls[nskip:last_item]
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

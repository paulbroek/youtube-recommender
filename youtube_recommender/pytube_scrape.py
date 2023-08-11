"""pytube_scrape.py, scraping metadata of videos through pytube.

pytube docs: 
    https://readthedocs.org/projects/python-pytube/downloads/pdf/stable/

example usage:
    ipy pytube_scrape.py -i -- --ncore 12 -sp -n 50 --channel_url https://www.youtube.com/channel/UC8butISFwT-Wl7EV0hUK0BQ

todo:
    - [] this whole script will be replaced by microservices, implemented in scrape_requests/scrape.py
"""

import argparse
import asyncio
import logging
import sys
from http.client import RemoteDisconnected
from multiprocessing import Pool
from time import time
from typing import Any, Dict, Final, List, Set

import pandas as pd
from pytube import Channel as PyTubeChannel  # type: ignore[import]
from pytube import YouTube as PyTubeVideo  # type: ignore[import]
# from pytube import Playlist, Search
from rarc_utils.log import get_create_logger
# from rarc_utils.sqlalchemy_base import get_async_session
from scrape_utils.core.db import get_async_session
# from youtube_recommender import config as config_dir
# from youtube_recommender.core.setup import psql_config
from youtube_recommender.core.setup import settings
from youtube_recommender.data_methods import data_methods as dm
from youtube_recommender.db.db_methods import refresh_view
# from youtube_recommender.db.helpers import (
#     get_keyword_association_rows_by_ids, get_video_ids_by_ids)
from youtube_recommender.db.helpers import get_video_ids_by_channel_ids
from youtube_recommender.settings import (CHANNEL_FIELDS, PYTUBE_VIDEOS_PATH,
                                          VIDEO_FIELDS)
from youtube_recommender.video_finder import load_feather, save_feather

logger = get_create_logger(
    cmdLevel=logging.INFO,
    color=1,
)

WITH_DESCRIPTION: Final[bool] = False
# WITH_DESCRIPTION: Final[bool] = True


# TODO: as of may '23, pytube Channel will not return all video urls, so this script no longer works
# can scrape single videos, and directly push them to postgres instead
def extract_video_fields(
    url: str, fields=VIDEO_FIELDS, isodate=False
) -> Dict[str, Any]:
    """Extract selected fields from PyTubeVideo object."""
    assert isinstance(url, str)

    youtube = PyTubeVideo(url)

    # pytube v15 fix, call vid.streams.first(), just to retrieve video description
    # TODO: is it slow?
    if WITH_DESCRIPTION:
        try:
            _ = youtube.streams.first()
        except Exception as e:
            pass

    res = {}
    # slow?
    for field in fields:
        try:
            res[field] = getattr(youtube, field)

        except RemoteDisconnected:
            logger.error(f"remote disconnected")
            return {}

        except Exception as e:
            # TODO: often means number of requests/second is too high
            logger.error(f"could not get attribute `{field}` from {youtube=} \n{e=!r}")
            raise

        if field == "publish_date" and isodate:
            res[field] = res[field].isoformat()

    return res


def extract_channel_fields(
    url: str,
    fields=CHANNEL_FIELDS,
) -> Dict[str, Any]:
    """Extract selected fields from Channel object."""
    assert isinstance(url, str)

    chan = PyTubeChannel(url)
    res = {}
    # slow?
    for field in fields:
        try:
            metadata = chan.initial_data["metadata"]["channelMetadataRenderer"]
            if field == "title":
                res["channel_name"] = metadata["title"]
            elif field == "channel_id":
                res["channel_id"] = metadata["externalId"]
            elif field == "description":
                res["channel_description"] = metadata["description"]
            else:
                res[field] = getattr(chan, field)
        except AttributeError:
            logger.error(f"cannot get {field=}")

    return res


def extract_multiple_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """Extract metadata from multiple urls. Caution: uses slow for loop."""
    res = []
    t0 = time()
    # slow?
    for url in urls:
        yt = PyTubeVideo(url)
        res.append(extract_video_fields(yt))

    elapsed: float = time() - t0
    download_rate: float = len(res) / elapsed
    logger.info(
        f"got {len(res):,} items in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )
    return res


def mp_extract_videos(urls: List[str], nprocess: int) -> List[Dict[str, Any]]:
    """Extract metadata from multiple urls using ultiprocessing ."""
    t0 = time()
    with Pool(processes=nprocess) as pool:
        res = pool.map(extract_video_fields, urls)

    elapsed: float = time() - t0
    download_rate: float = len(res) / elapsed
    logger.info(
        f"got {len(res):,} items in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )

    return res


def mp_extract_channels(res: List[Dict[str, Any]], nprocess: int):
    """Extract metadata for multiple videos + channel names using multiprocessing."""
    # get unique channels
    channel_urls: Set[str] = set(r["channel_url"] for r in res)

    t0 = time()
    with Pool(processes=nprocess) as pool:
        res = pool.map(extract_channel_fields, channel_urls)

    elapsed: float = time() - t0
    download_rate: float = len(res) / elapsed
    logger.info(
        f"got {len(res):,} channel metadatas in {elapsed:.2f} secs ({download_rate:.1f} items/sec)"
    )

    return res


loop = asyncio.get_event_loop()

parser = argparse.ArgumentParser(description="Defining pytube_scrape parameters")
parser.add_argument(
    "--ncore",
    default=8,
    help="Max cores to use for multiprocessing",
)
parser.add_argument(
    "--cfg_file",
    type=str,
    default="postgres.cfg",
    help="choose a configuration file",
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
    "--only_new",
    action="store_true",
    default=False,
    help="only scrape video ids that are not seen in db",
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

    # psql = load_config(
    #     db_name="youtube",
    #     cfg_file=args.cfg_file,
    #     config_dir=config_dir,
    #     starts_with=True,
    # )
    # async_session = get_async_session(psql_config)
    async_session = get_async_session(settings.db_async_connection_str)

    assert isinstance(args.channel_url, str), "pass url as string"

    nskip: int = int(args.skip)
    nitems: int = int(args.nitems)
    ncore: int = int(args.ncore)

    # todo: load cannot be used to push items, since object relation to db is lost
    if args.load:
        df = load_feather(PYTUBE_VIDEOS_PATH)

    else:
        vurls: PyTubeChannel = PyTubeChannel(args.channel_url)

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

        # todo: get num_subscribers through beautifulsoup or PyTubeVideo API
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

    # ask user to refresh materialized view
    view = "top_channels_with_comments"
    input_ = input("refresh view {}? Type `y`: ".format(view))
    if input_ == "y":
        refresh_view(view)

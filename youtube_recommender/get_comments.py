r"""get_comments.py.

Get all comments for a given YouTube video / channel

install downloader first:
    pip install youtube_comment_downloader

    github repo:
        https://github.com/egbertbouman/youtube-comment-downloader/blob/master/youtube_comment_downloader/downloader.py

Example usage:

    # use nproc == 1 to only use generators, and nproc > 1 to use multiprocessing pool
    ipy get_comments.py -i -- --channel_ids UCOjD18EJYcsBog4IozkF_7w --max 20 --nproc 6
    ipy get_comments.py -i -- --channel_ids UCOjD18EJYcsBog4IozkF_7w --max 20 --nproc 1

    # another example: get top 10 channel ids:
    # SELECT string_agg(id, ' ') FROM top_channels LIMIT 10;

    ipy get_comments.py -i -- --nproc 10 --channel_ids UCkw4JCwteGrDHIsyIIKo4tQ UCOjD18EJYcsBog4IozkF_7w UCs6nmQViDpUw0nuIx9c_WvA UCsvqVGtbbyHaMoevxPAq9Fg UC8butISFwT-Wl7EV0hUK0BQ UC4xKdmAXFh4ACyhpiQ_3qBw

    in one line:
        docker exec -it postgres-master bash -c 'psql -d youtube -U postgres -c "SELECT id FROM top_channels LIMIT 10;" --quiet --csv > /output/channel_ids.csv'
        # turn column into space seperated string
        sed 1d ~/other_repos/postgres_output/channel_ids.csv | tr "\n" " " | xclip

        ipy get_comments.py -i -- --nproc 10 --channel_ids $(xclip -o) --max 0 -p

    # load any dataset from disk:
    ipy get_comments.py -i -- --load_jl

    # load dataset and save to feather
    ipy get_comments.py -i -- --load_jl --save_feather

    # load from feather
    ipy get_comments.py -i -- --load_feather

    # load from feather and push to database
    ipy get_comments.py -i -- --load_feather --push_db

Datasets explained:
    comments.jl         holds raw data from YouTube
    comments.feather    holds parsed rows. rows that can be parsed to SQLAlchemy objects

How to get comments for specific channel_ids:
    - run a specific query that returns the channel ids of channels without comments, example:

    (run first: refresh materialized view top_channels_with_comments; )
    docker exec -it postgres-master \                                                              
        psql -d youtube -U postgres -c "select channel_id from top_channels_with_comments where comment_count = 0 and channel_id IS NOT NUll" --quiet --csv > ~/other_repos/postgres_output/channel_ids.csv

    then save channel_ids in xclip:
        sed 1d ~/other_repos/postgres_output/channel_ids.csv | tr "\r" " " | xclip

    and finally run get_comments.py:
        ipy get_comments.py -i -- --nproc 12 --max 0 --channel_ids $(xclip -o) -p --save_feather

    todo:
        - this whole script will be replaced by microservices, implemented in scrape_requests/*
"""

import argparse
import asyncio
import logging
import sys
from functools import partial
from itertools import chain
from multiprocessing import Pool
from typing import Any, Dict, Iterator, List

import pandas as pd
from rarc_utils.decorators import items_per_sec
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session
from youtube_comment_downloader.downloader import \
    YoutubeCommentDownloader  # type: ignore[import]
from youtube_recommender import config as config_dir
from youtube_recommender.comments_methods import comments_methods as cm
from youtube_recommender.core.setup import psql_config as psql
from youtube_recommender.data_methods import data_methods as dm
from youtube_recommender.db.helpers import get_video_ids_by_channel_ids
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (COMMENTS_FEATHER_FILE,
                                          COMMENTS_JL_FILE)

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

loop = asyncio.get_event_loop()
downloader = YoutubeCommentDownloader()

sort = True
language = "en"


# fixate sort_by and language parameters
get_comments_by_video_id = partial(
    downloader.get_comments, sort_by=sort, language=language
)


def get_comments_wrapper(video_id: str) -> Iterator[Dict[str, Any]]:
    """Add video_id to item dict."""
    for item in get_comments_by_video_id(video_id):
        item["video_id"] = video_id
        yield item


def get_comments_list(video_id: str) -> List[Dict[str, Any]]:
    """Return comments for a list of video_ids."""
    return list(get_comments_wrapper(video_id))


def receiver(generator: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    """Take items from comment generator, show progress to user."""
    videos_seen = set()
    for count, item in enumerate(generator, start=1):
        videos_seen.add(item["video_id"])
        sys.stdout.write(
            "Downloaded %d comment(s). nvid=%d\r" % (count, len(videos_seen))
        )
        sys.stdout.flush()

        yield item


@items_per_sec
def receive_in_parallel(nprocess: int, vids: List[str]) -> List[Dict[str, Any]]:
    """Receive lists of comments in parallel.

    Side effect: writes to export/comments.jl file
    """
    # clean file first
    if not args.reuse_file:
        im.reset_jsonlines(COMMENTS_JL_FILE)

    pool = Pool(processes=nprocess)

    lres = []
    total_comments = 0
    # can this be rewritten using with ... ?
    for i, x in enumerate(pool.imap_unordered(get_comments_list, vids)):
        total_comments += len(x)
        sys.stdout.write(
            f"Processed {i:,} video(s). Total comments: {total_comments:,}\r"
        )
        sys.stdout.flush()
        # write intermediary results to jsonlines file
        im.append_jsonlines(COMMENTS_JL_FILE, x)

        lres.append(x)

    return sum(lres, [])


parser = argparse.ArgumentParser(description="Define get_coments parameters")
parser.add_argument(
    "--nproc",
    default=1,
    type=int,
    help="Max number of processes to use for multiprocessing",
)
parser.add_argument(
    "--cfg_file",
    type=str,
    default="postgres.cfg",
    help="choose a configuration file",
)
parser.add_argument(
    "--channel_ids",
    default=[],
    nargs="*",
    help="channel_id to download comments for",
)
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
    "--reuse_file",
    action="store_true",
    default=False,
    help="reuse export/comments.jl file",
)
parser.add_argument(
    "-p",
    "--push_db",
    action="store_true",
    default=False,
    help="push (new) comments to PostgreSQL`",
)
parser.add_argument(
    "--load_jl",
    action="store_true",
    default=False,
    help="load .jl dataset from disk",
)
parser.add_argument(
    "--load_feather",
    action="store_true",
    default=False,
    help="load .feather dataset from disk",
)
parser.add_argument(
    "--save_feather",
    action="store_true",
    default=False,
    help="save .feather dataset to disk",
)
parser.add_argument(
    "--dryrun",
    action="store_true",
    default=False,
    help="only import modules",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # psql = load_config(
    #     db_name="youtube",
    #     cfg_file=args.cfg_file,
    #     config_dir=config_dir,
    #     starts_with=True,
    # )

    async_session = get_async_session(psql)

    LOADED_DF = False

    if args.load_jl:
        df = im.load_jsonlines(COMMENTS_JL_FILE)
        df = df.pipe(cm.comments_pipeline)
        LOADED_DF = True

    elif args.load_feather:
        df = im.load_feather(COMMENTS_FEATHER_FILE, what="comment")
        LOADED_DF = True

    if not LOADED_DF:
        if args.channel_ids:
            video_ids = loop.run_until_complete(
                get_video_ids_by_channel_ids(async_session, args.channel_ids)
            )

        else:
            video_ids = args.video_ids
            assert isinstance(
                video_ids[0], str
            ), "please pass at least one valid video_id"

        if args.skip > 0:
            video_ids = video_ids[args.skip :]

        if args.max > 0:
            video_ids = video_ids[: args.max]

        logger.info(f"selected {len(video_ids):,} videos")

        print(f"number of videos to get comments for: {len(video_ids):,}")

        generators = (get_comments_wrapper(youtube_id) for youtube_id in video_ids)
        big_generator = chain(*generators)

        if args.dryrun:
            sys.exit()

        if args.nproc == 1:
            items = list(receiver(big_generator))
        else:
            items = receive_in_parallel(args.nproc, video_ids)

        df = pd.DataFrame(items).pipe(cm.comments_pipeline)

    if args.save_feather:
        im.save_feather(df, COMMENTS_FEATHER_FILE, "comment")

    # push new comments to db
    if args.push_db:
        res = loop.run_until_complete(
            dm.push_comments(df, async_session, autobulk=True, returnExisting=False)
        )

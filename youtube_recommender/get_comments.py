"""get_comments.py.

Get all comments for a given YouTube video / channel

install downloader first:
    pip install youtube_comment_downloader

    github repo:
        https://github.com/egbertbouman/youtube-comment-downloader/blob/master/youtube_comment_downloader/downloader.py

Example usage:

    # use nproc == 1 to only use generators, and nproc > 1 to use multiprocessing pool
    ipy get_comments.py -i -- --channel_id UCOjD18EJYcsBog4IozkF_7w --max 20 --nproc 6
    ipy get_comments.py -i -- --channel_id UCOjD18EJYcsBog4IozkF_7w --max 20 --nproc 1
"""

import argparse
import asyncio
import sys
from functools import partial
from itertools import chain
from multiprocessing import Pool
from typing import Any, Dict, Iterator, List

import pandas as pd
from rarc_utils.decorators import items_per_sec
from rarc_utils.sqlalchemy_base import get_async_session
from youtube_comment_downloader.downloader import \
    YoutubeCommentDownloader  # type: ignore[import]
from youtube_recommender.db.helpers import get_video_ids_by_channel_ids
from youtube_recommender.db.models import psql

async_session = get_async_session(psql)

loop = asyncio.get_event_loop()
downloader = YoutubeCommentDownloader()

parser = argparse.ArgumentParser(description="Define get_coments parameters")
parser.add_argument(
    "--nproc",
    default=1,
    type=int,
    help="Max number of processes to use for multiprocessing",
)
parser.add_argument(
    "--channel_id",
    type=str,
    help="channel_id to download comments for",
)
parser.add_argument(
    "--video_id",
    help="video_id to download comments for, if channel_id was not passed",
)
parser.add_argument(
    "--max",
    type=int,
    help="max videos to get comments for",
)

args = parser.parse_args()

sort = True
language = "en"

if args.channel_id:
    channel_ids = [args.channel_id]
    video_ids = loop.run_until_complete(
        get_video_ids_by_channel_ids(async_session, channel_ids)
    )

else:
    video_ids = [args.video_id]

if args.max:
    video_ids = video_ids[: args.max]

print(f"number of videos to get comments for: {len(video_ids):,}")

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
    with Pool(processes=nprocess) as pool:
        res = pool.map(get_comments_list, vids)

    return sum(res, [])


# chain generators
# generators = (
#     get_comments_by_video_id(youtube_id) for youtube_id in video_ids
# )
generators = (get_comments_wrapper(youtube_id) for youtube_id in video_ids)
# generator = (
#     downloader.get_comments(youtube_id, sort, language)
#     # if youtube_id
#     # else downloader.get_comments_from_url(youtube_url, sort, language)
# )

big_generator = chain(*generators)

if args.nproc == 1:
    items = list(receiver(big_generator))
else:
    items = receive_in_parallel(args.nproc, video_ids)

# items = list(generator)
# items = list(big_generator)
df = pd.DataFrame(items)

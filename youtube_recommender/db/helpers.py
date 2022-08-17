"""helpers.py, helper methods for SQLAlchemy models, listed in models.py."""

import logging
import re
import zlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from aiocache import Cache, cached  # type: ignore[import]
from aiocache.serializers import PickleSerializer  # type: ignore[import]
from rarc_utils.sqlalchemy_base import add_many, create_many
from sqlalchemy import and_
from sqlalchemy.future import select  # type: ignore[import]

from ..core.types import ChannelId, VideoId, VideoRec
from ..settings import HOUR_LIMIT, PSQL_HOURS_AGO
from .models import Caption, Channel, Comment, Video, queryResult

logger = logging.getLogger(__name__)

time_pattern = re.compile(r"(\d+:\d+:\d+)(.+)")
# a group with time pattern and (hopefully) the name of the chapter, might leave orphaned ']'  or ')' bracket
# removing this remainder bracket, use a replace pattern for now
replace_pat = re.compile(r"^[\]|\)-]+")

# cache = Cache(Cache.REDIS, serializer=JsonSerializer())


def parse_time(row, levels=("seconds", "minutes", "hours")) -> Optional[timedelta]:
    """Parse time from YouTube chapter as generic as possible.

    Caution: sometimes only M:S format: 23:20, sometimes full H:M:S format: 15:10:10
    """
    s = row.s
    # split and reverse order (seconds first)
    parts = s.split(":")[::-1]

    # determine number of time parts
    if len(parts) > 3:
        logger.error(f"too many parts: {s=}, {row.video_id=}")
        return None

    dd_level = defaultdict(int)

    for part, level in zip(parts, levels):
        dd_level[level] = int(part)

    # create timedelta object
    return timedelta(**dd_level)


def find_chapter_locations(video_recs: List[VideoRec], display=False) -> List[dict]:
    """Find lines in video description that capture time link data.

    Example:
        ⌨️ (0:00:00) Introduction
        ⌨️ (0:00:34) Colab intro (importing wine dataset)
    """
    ret = []
    for video_rec in video_recs:
        assert isinstance(video_rec, dict)

        rec_factory = lambda: {
            "video_id": video_rec["id"],
            "video_description": video_rec["description"],
            "video_length": video_rec["length"],
            "video_end": timedelta(seconds=video_rec["length"]),
        }

        res = time_pattern.findall(video_rec["description"])
        if len(res) > 0:
            if display:
                print(f"{video_rec['title']=}, \n{res=} \n\n")

        for r in res:
            rec = rec_factory()
            rec["s"] = r[0]
            rec["name"] = re.sub(replace_pat, "", r[1]).strip()
            ret.append(rec)

    return ret


def chapter_locations_to_df(ret: List[dict]) -> pd.DataFrame:
    """Parse list of chapter locations to pd.DataFrame."""
    assert isinstance(ret, list), f"{type(ret)=}, should be list"
    df = pd.DataFrame(ret)

    if df.empty:
        return df

    df["len"] = df["s"].map(len)

    # prepend a 0 when first item has len 1
    # df['s'] = np.where(df['len'] == 7, '0' + df['s'], df['s'])

    # todo: dismiss time strings with len >= 9?
    df["start"] = df.apply(parse_time, axis=1)
    df["start_seconds"] = df["start"].dt.total_seconds().astype(int)

    # calculate end time, using next start time, if available
    by_vid = df.groupby("video_id")
    df["end"] = by_vid["start"].shift(-1)
    # make last chapter.end equal to video length
    df["end"] = np.where(df["end"].isnull(), df["video_end"], df["end"])
    df["end_seconds"] = df["end"].dt.total_seconds().astype(int)

    df = df.sort_values(["start", "end"])
    # drop duplicate (start, name) rows
    df = df.drop_duplicates(subset=["video_id", "name", "start"])

    # add sub_id per video
    df["sub_id"] = by_vid["video_id"].cumcount()

    return df


async def create_many_items(asession, *args, **kwargs):
    """Create many SQLAlchemy model items in db."""
    # asession = args[0]
    async with asession() as session:
        items = await create_many(session, *args, **kwargs)

    return items


async def add_many_items(asession, model, itemDicts, nameAttr="name"):
    async with asession() as session:
        items = await add_many(session, model, itemDicts, nameAttr=nameAttr)

    return items


def get_all(session, model):
    """Get all items of a model.

    example usage:

        videos = get_all(psession, Video)
        channels = get_all(psession, Channel)
    """
    stmt = select(model).filter()

    return list(session.execute(stmt).scalars())


async def get_keyword_association_rows_by_ids(asession, video_ids: List[VideoId]):
    """Get existing video ids.

    usage:
        kws = loop.run_until_complete(get_keyword_association_rows_by_ids(async_session, df.video_id.to_list()))
    """
    q = select(Video.id).filter(Video.id.in_(video_ids))

    async with asession() as session:
        video_ids = (await session.execute(q)).scalars().all()

        fmt_ids = "'{0}'".format("', '".join(video_ids))
        kws = """SELECT * FROM video_keyword_association WHERE video_id IN ({});""".format(
            fmt_ids
        )
        # logger.info(f"{kws=}")

        kw_rows = (await session.execute(kws)).fetchall()

    return kw_rows


async def get_video_ids_by_ids(asession, video_ids: List[VideoId]) -> List[VideoId]:
    """Get existing video ids.

    usage:
        ids = loop.run_until_complete(get_video_ids_by_ids(async_session, df.video_id.to_list()))
    """
    q = select(Video.id).filter(Video.id.in_(video_ids))

    async with asession() as session:
        video_ids = (await session.execute(q)).scalars().all()

    return video_ids


# @cached(ttl=None, cache=cache)
async def get_top_videos_by_channel_ids(
    asession, channel_ids: List[ChannelId]
) -> pd.DataFrame:
# ) -> List[dict]:
    """Get top videos by channel ids."""
    # todo: I use inner method to only cache `channel_ids`, is there a work around for this?
    @cached(ttl=None, cache=Cache.REDIS, serializer=PickleSerializer())
    async def inner(channel_ids=channel_ids):
        async with asession() as session:
            fmt_ids = "'{0}'".format("', '".join(channel_ids))
            query = """SELECT * FROM top_videos WHERE channel_id IN ({});""".format(fmt_ids)
            res = await session.execute(query)

            rows: List[dict] = res.fetchall()
            logger.info(f"fetched {len(rows):,} rows from db")

        # return rows
        return pd.DataFrame(rows)

    return await inner(channel_ids)

async def get_videos_by_ids(asession, video_ids: List[VideoId]):
    """Get Videos by video_ids."""
    async with asession() as session:
        query = select(Video).where(Video.id.in_(video_ids))
        res = await session.execute(query)

        instances = res.scalars().fetchall()

    return instances


async def get_video_ids_by_channel_ids(asession, channel_ids: List[ChannelId]):
    """Get vidoe_ids by channel_ids."""
    query = select(Video.id).where(Video.channel_id.in_(channel_ids))

    async with asession() as session:
        res = await session.execute(query)

        instances = res.scalars().fetchall()

    return instances


async def get_videos_by_query(
    asession, query: str, maxHoursAgo: int = PSQL_HOURS_AGO, n=200
):
    """Get Videos associated with `query` from db.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
    maxHoursAgo = min(maxHoursAgo, HOUR_LIMIT)
    since = datetime.utcnow() - timedelta(hours=maxHoursAgo)

    # uses materialized view `last_videos`, assuming it refreshes on every query_result record insert
    async with asession() as session:

        # todo: this can be done with SQLAlchemy models, raw SQL is not needed
        query_ = f"SELECT * FROM last_videos WHERE query = '{query}' AND qr_updated > '{since.isoformat()}' LIMIT {n};"
        # logger.info(f"{query_=}")

        res = await session.execute(query_)

        instances = res.mappings().fetchall()

    return instances


async def get_channels_by_video_ids(
    asession, video_ids: List[str]
) -> Dict[ChannelId, Channel]:
    """Get Channels by video_ids.

    Used to get all user accounts that replied to a list of videos
    """
    q = select(Channel).join(Comment).join(Video).where(Comment.video_id.in_(video_ids))

    async with asession() as session:
        res = await session.execute(q)
        channels: List[Channel] = res.fetchall()

    if len(channels) == 0:
        logger.warning(
            f"no channels received, are you trying to get channels from comments before pushing the comments?"
        )

    return {c.id: c for c in channels}


async def get_top_channels_with_comments(asession, dropna=False) -> pd.DataFrame:
    """Get top channels from materialized view."""
    query = """SELECT * FROM top_channels_with_comments;"""

    async with asession() as session:
        res = await session.execute(query)

        rows: List[dict] = res.fetchall()

    df = pd.DataFrame(rows)
    if dropna:
        df = df.dropna()

    return df


async def get_comments_by_popularity():
    """Get comments by popularity."""
    raise NotImplementedError


async def get_comments_by_video_ids(
    asession, video_ids: List[str]
) -> List[Dict[str, Any]]:
    """Get Comments by video_ids."""
    # q = select(Comment).join(Video).filter(Video.id.in_(video_ids))
    ids_str = "', '".join(video_ids)
    q = """ 
        SELECT 
            video_channel.name AS vid_channel_name, 
            video.title AS video_title, 
            comment.*,
            comment_channel.name AS com_channel_name
        FROM video
        LEFT JOIN channel AS video_channel ON video.channel_id = video_channel.id
        LEFT JOIN comment ON video.id = comment.video_id
        LEFT JOIN channel AS comment_channel ON comment.channel_id = comment_channel.id
        WHERE video.id IN ('{}')
    """.format(
        ids_str
    )

    async with asession() as session:
        res = await session.execute(q)

        instances: List[Dict[str, Any]] = res.mappings().fetchall()

    return instances


async def get_captions_by_vids(
    asession, video_ids: List[VideoId], maxHoursAgo: int = PSQL_HOURS_AGO
):
    """Get Captions by video_ids.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
    maxHoursAgo = min(maxHoursAgo, HOUR_LIMIT)
    since = datetime.utcnow() - timedelta(hours=maxHoursAgo)

    async with asession() as session:
        query = select(Caption).where(
            and_(Caption.video_id.in_(video_ids), Caption.updated > since)
        )
        res = await session.execute(query)

        instances = res.scalars().fetchall()

    logger.info(f"using {len(instances)} existing captions")

    return instances


def get_last_query_results(session, query: str, maxHoursAgo: int = PSQL_HOURS_AGO):
    """Get last query results.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
    maxHoursAgo = min(maxHoursAgo, HOUR_LIMIT)
    since = datetime.utcnow() - timedelta(hours=maxHoursAgo)

    stmt = (
        select(queryResult)
        .filter(queryResult.query == query)
        .where(queryResult.updated > since)
        .order_by(queryResult.updated.desc())
    )
    return list(session.execute(stmt).scalars())


def compress_caption(caption: str) -> bytes:
    """Compress str caption using zlib, saves ~ 50% storage."""
    assert isinstance(caption, str)
    return zlib.compress(caption.encode())


def decompress_caption(compr: bytes) -> str:
    """Decompress str caption using zlib."""
    assert isinstance(compr, bytes)
    return zlib.decompress(compr).decode()

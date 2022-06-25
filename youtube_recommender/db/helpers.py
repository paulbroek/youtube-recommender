"""helpers.py, helper methods for SQLAlchemy models, listed in models.py."""

import logging
import re
import zlib
from datetime import datetime, time, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd
from rarc_utils.sqlalchemy_base import create_many
from sqlalchemy import and_
from sqlalchemy.future import select  # type: ignore[import]

from ..core.types import VideoId
from ..settings import HOUR_LIMIT, PSQL_HOURS_AGO
from .models import Caption, Chapter, Video, queryResult

# from .models import *

logger = logging.getLogger(__name__)

time_pattern = re.compile(r"\d+:\d+:\d+")


def match_video_locations():
    """Find lines in video description that capture time link data.

    Example:
        ⌨️ (0:00:00) Introduction
        ⌨️ (0:00:34) Colab intro (importing wine dataset)
    """
    pass


def parse_isotime(row) -> Optional[time]:
    # todo: datetime.time cannot be used, since sometimes hour > 24, use your own data structure 
    # use interval?
    try:
        return time.fromisoformat(row.s)
    except ValueError:
        logger.error(f"cannot parse time: {row.s}, {row.video_id=}")
        return None

def parse_time(row, level=0):
    pass


def find_all_locations(videos: List[Video], display=False) -> List[dict]:
    ret = []
    for video in videos:
        rec_factory = lambda: dict(
            video_id=video.id, video_description=video.description
        )
        res = time_pattern.findall(video.description)
        if len(res) > 0:
            if display:
                print(f"{video.title=}, \n{res=} \n\n")

        for i, r in enumerate(res):
            rec = rec_factory()
            rec["s"] = r
            # can parse time?
            # start = parse_isotime(r)
            # end comes after parsing all of them
            # create Chapter objects
            # Chapter(name=r, video=video, sub_id=i, start=0, end=0)
            ret.append(rec)

    return ret

def chapter_locations_to_df(ret: List[dict]) -> pd.DataFrame:
    df = pd.DataFrame(ret)
    df['len'] = df['s'].map(len)

    # prepend a 0 when first item has len 1
    df['s'] = np.where(df['len'] == 7, '0' + df['s'], df['s'])

    # todo: dismiss time strings with len >= 9? 

    # df['start'] = df[['video_id','s']].map(parse_isotime)
    df['start'] = df.apply(parse_isotime, axis=1)

    return df

async def create_many_items(
    asession, model, itemDicts, nameAttr="name", returnExisting=False
):
    """Create many SQLAlchemy model items in db."""
    async with asession() as session:
        items = await create_many(
            session, model, itemDicts, nameAttr=nameAttr, returnExisting=returnExisting
        )

    return items


def get_all(session, model):
    """Get all items of a model.

    example usage:

        videos = get_all(psession, Video)
        channels = get_all(psession, Channel)
    """
    stmt = select(model).filter()

    return list(session.execute(stmt).scalars())


async def get_videos_by_ids(asession, video_ids: List[VideoId]):
    """Get Videos by video_ids from db."""
    async with asession() as session:
        query = select(Video).where(Video.id.in_(video_ids))
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


async def get_captions_by_vids(
    asession, video_ids: List[VideoId], maxHoursAgo: int = PSQL_HOURS_AGO
):
    """Get Captions by video_ids from db.

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
    """Get last query results from db.

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

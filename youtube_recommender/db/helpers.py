"""helpers.py, helper methods for SQLAlchemy models, listed in models.py."""

import logging
import re
import zlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd
from rarc_utils.sqlalchemy_base import create_many
from sqlalchemy import and_
from sqlalchemy.future import select  # type: ignore[import]

from ..core.types import VideoId, VideoRec
from ..settings import HOUR_LIMIT, PSQL_HOURS_AGO
from .models import Caption, Video, queryResult

logger = logging.getLogger(__name__)

time_pattern = re.compile(r"(\d+:\d+:\d+)(.+)")
# a group with time pattern and (hopefully) the name of the chapter, might leave orphaned ']'  or ')' bracket
# removing this remainder bracket, use a replace pattern for now
replace_pat = re.compile(r"^[\]|\)-]+")


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


async def get_keyword_association_rows_by_ids(asession, video_ids: List[VideoId]):
    """Get existing video ids from db.

    usage:
        kws = loop.run_until_complete(get_keyword_association_rows_by_ids(async_session, df.video_id.to_list()))
    """
    q = select(Video.id).filter(Video.id.in_(video_ids))

    async with asession() as session:
        video_ids = (await session.execute(q)).scalars().all()

        fmt_ids = "'{0}'".format("', '".join(video_ids))
        kws = (
            """SELECT * FROM video_keyword_association WHERE video_id IN ({});""".format(
                fmt_ids
            )
        )
        # logger.info(f"{kws=}")

        kw_rows = (await session.execute(kws)).fetchall()

    return kw_rows

async def get_video_ids_by_ids(asession, video_ids: List[VideoId]) -> List[VideoId]:
    """Get existing video ids from db.

    usage:
        ids = loop.run_until_complete(get_video_ids_by_ids(async_session, df.video_id.to_list()))
    """
    q = select(Video.id).filter(Video.id.in_(video_ids))

    async with asession() as session:
        video_ids = (await session.execute(q)).scalars().all()

    return video_ids


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

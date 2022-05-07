"""helpers.py, helper methods for SQLAlchemy models, listed in models.py."""
import logging
import zlib
from datetime import datetime, timedelta
from typing import Any, List, Optional  # Dict, Set, Tuple

import pandas as pd
from rarc_utils.sqlalchemy_base import aget_str_mappings as aget_str_mappings_custom
from rarc_utils.sqlalchemy_base import create_many
from rarc_utils.sqlalchemy_base import get_str_mappings as get_str_mappings_custom
from sqlalchemy import and_
from sqlalchemy.future import select

from ..core.types import VideoId
from ..settings import PSQL_HOURS_AGO
from .models import Caption, Video, queryResult

# from .models import *

logger = logging.getLogger(__name__)

# async def aget_all(asession, model, skip: int = 0, limit: int = 100):
async def aget_all(session, model=None, skip: int = 0, limit: int = 100):
    """Get all items for a model.

    usage:
        loop.run_until_complete(run_in_session(async_session, aget_all, model=Habbit))
        loop.run_until_complete(run_in_session(async_session, aget_all, model=genericTask))
    """
    assert model is not None
    # async with asession() as session:
    query = select(model).offset(skip).limit(limit)
    res = await session.execute(query)
    return list(res.scalars())


async def aget_by_name(session, model, name: str) -> Optional[Any]:
    """Get item for a given model by name.

    used to search for items

    usage:
        loop.run_until_complete(run_in_session(async_session, aget_by_name, model=genericTask, name='read'))
    """
    # async with asession() as session:
    query = select(model).filter_by(name=name).limit(1)
    res = (await session.execute(query)).first()
    if res is not None:
        return res[0]
    return res


# str_mappings = loop.run_until_complete(aget_str_mappings(psql))
async def aget_str_mappings(psqConfig, models=()):

    return await aget_str_mappings_custom(psqConfig, models)


# str_mappings = get_str_mappings(s)
def get_str_mappings(psqConfig, models=()):

    return get_str_mappings_custom(psqConfig, models)


async def create_many_items(
    asession, model, itemDicts, nameAttr="name", returnExisting=False
):

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
):  # qr: queryResult
    """Get Videos associated with `queryResult` from db.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
    since = datetime.utcnow() - timedelta(hours=maxHoursAgo)

    # uses materialized view `last_videos`, assuming it refreshes on every query_result record insert
    async with asession() as session:

        # todo: this can be done with SQLAlchemy models, raw SQL is not needed
        query_ = f"SELECT * FROM last_videos WHERE query = '{query}' AND qr_updated > '{since.isoformat()}' LIMIT {n};"
        logger.info(f"{query_=}")

        res = await session.execute(query_)

        instances = res.mappings().fetchall()

    return instances


async def get_captions_by_video_ids(
    asession, video_ids: List[VideoId], maxHoursAgo: int = PSQL_HOURS_AGO
):
    """Get Captions by video_ids from db.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
    since = datetime.utcnow() - timedelta(hours=maxHoursAgo)

    async with asession() as session:
        query = select(Caption).where(
            and_(Caption.video_id.in_(video_ids), Caption.updated > since)
        )
        res = await session.execute(query)

        instances = res.scalars().fetchall()

    return instances


def get_last_query_results(session, query: str, maxHoursAgo: int = PSQL_HOURS_AGO):
    """Get last query results from db.

    maxHoursAgo:    only include captions that are less than `maxHoursAgo`
    """
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

"""db_methods.py.

methods to help with deleting and updating data in the database
used to run independently from main codebase
"""

import asyncio
import logging
from typing import List

from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import (get_async_db, get_async_session,
                                        get_session)
from sqlalchemy import delete, select
from youtube_recommender.db.models import Channel, Chapter, Video
from youtube_recommender.utils.misc import load_config

LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"

psql = load_config()
psession = get_session(psql)()


async def get_existing_video_ids(asession, video_ids: List[str]) -> List[str]:
    """Get existing video ids from db.

    usage:
        ids = get_existing_video_ids(async_session, df.video_id.to_list())
    """
    q = select(Video.id).join(Channel).where(Video.id.in_(video_ids))

    async with asession() as session:
        video_ids = (await session.execute(q)).scalars().all()

    return video_ids


async def delete_videos_from_channel(asession, channel_id: str):
    """Delete all video rows related to a Channel, including video_keyword associations.

    usage:
        channel_id = "UCsvqVGtbbyHaMoevxPAq9Fg"
        res = loop.run_until_complete(delete_videos_from_channel(async_session, channel_id))
    """
    # first delete association table records
    videosq = select(Video.id).join(Channel).where(Channel.id == channel_id)

    async with asession() as session:
        video_ids = (await session.execute(videosq)).scalars().all()
        print(video_ids[:3])

        # select all keywords
        fmt_ids = "'{0}'".format("', '".join(video_ids))
        delete_kw = (
            """DELETE FROM video_keyword_association WHERE video_id IN ({});""".format(
                fmt_ids
            )
        )
        # logger.info(f"{delete_kw=}")

        _ = await session.execute(delete_kw)

        # logger.info(f"{kw_res=}, {dir(kw_res)=} \n{kw_res.one()=}")
        # logger.info(f"{len(kw_res)=:,} {kw_res[:3]=}")

        # now chapters, videos and channel can be deleted
        dchap = delete(Chapter).where(Chapter.video_id.in_(video_ids))
        dvid = delete(Video).where(Video.id.in_(video_ids))
        dchan = delete(Channel).where(Channel.id == channel_id)

        # chapter_delete_result = video_id
        chapter_delete_result = await session.execute(dchap)
        video_delete_result = await session.execute(dvid)
        channel_delete_result = await session.execute(dchan)
        logger.info(
            f"{chapter_delete_result=}, {video_delete_result=} {channel_delete_result=}"
        )


if __name__ == "__main__":
    logger = setup_logger(
        cmdLevel=logging.INFO, saveFile=0, savePandas=0, color=1, fmt=LOG_FMT
    )

    psession = get_session(psql)()
    async_session = get_async_session(psql)
    async_db = get_async_db(psql)()

    loop = asyncio.new_event_loop()

    # todo: remove lines
    channel_id = "UCsvqVGtbbyHaMoevxPAq9Fg"
    res = loop.run_until_complete(delete_videos_from_channel(async_session, channel_id))

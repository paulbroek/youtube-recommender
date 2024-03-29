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
from youtube_recommender import config as config_dir
from youtube_recommender.core.setup import psql_config as psql
from youtube_recommender.core.types import ChannelId
from youtube_recommender.db.models import Channel, Chapter, Video
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import CHAPTERS_JL_FILE

LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"

# psql = load_config(db_name="youtube", cfg_file="postgres.cfg", config_dir=config_dir)
psession = get_session(psql)()

logger = logging.getLogger(__name__)


def refresh_view(vw: str) -> None:
    """Refresh materialized view."""
    query = """REFRESH MATERIALIZED VIEW {};""".format(vw)
    logger.info(f"running query: {query}")
    psession.execute(query)
    logger.info("finished query")


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


async def set_educational_by_channel_id(asession, channel_ids: List[ChannelId]):
    """Set all videos from a list of channel_ids to is_educational = t.

    Get channel_ids of top channels:
        # SELECT array_to_string(array_agg(id), ',') FROM top_channels LIMIT 4
        SELECT array_agg(format('''%s''', id)) FROM top_channels LIMIT 4;
        but check the channels first!: SELECT * FROM top_channesl LIMIT 4

    usage:
        channel_ids = ['UCkw4JCwteGrDHIsyIIKo4tQ','UCs6nmQViDpUw0nuIx9c_WvA','UCsvqVGtbbyHaMoevxPAq9Fg','UC8butISFwT-Wl7EV0hUK0BQ']
        loop.run_until_complete(set_educational_by_channel_id(async_session, channel_ids))
    """
    fmt_ids = "'{0}'".format("', '".join(channel_ids))
    q = """ 
    UPDATE video
    SET is_educational = 't'
    FROM channel
    WHERE channel.id IN ({}) AND channel.id = video.channel_id;
    """.format(
        fmt_ids
    )

    logger.info(f"q: \n\n{q}")

    async with asession() as session:
        await session.execute(q)


def migrate_chapter_ids_to_composite(session) -> None:
    """Migrate old chapter ids (UUID) to composites.

    Composite: {video_id}-{sub_id}
    """
    q = select(Chapter)
    chapters = session.execute(q).scalars().all()
    for c in chapters:
        c.id = f"{c.video_id}-{c.sub_id}"

    cc = [c.json() for c in chapters]
    # session.commit()
    return cc


def create_chapters_from_json(session, file=CHAPTERS_JL_FILE) -> None:
    df = im.load_jsonlines(file).drop_duplicates(subset="id")
    assert not df.empty
    res = df.to_dict("records")

    # raise Exception
    chapters = [Chapter.from_json(r) for r in res]
    session.add_all(chapters)
    session.commit()


if __name__ == "__main__":
    logger = setup_logger(
        cmdLevel=logging.INFO, saveFile=0, savePandas=0, color=1, fmt=LOG_FMT
    )

    # psession = get_session(psql)()
    async_session = get_async_session(psql)
    async_db = get_async_db(psql)()

    loop = asyncio.new_event_loop()

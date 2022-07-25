"""create_educational_videos_dataset.py.

get videos with is_educational = 't' from db, and extract video descriptions
save to feather file
"""

import argparse
import logging

import pandas as pd
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_session
# from sqlalchemy.future import select  # type: ignore[import]
# from youtube_recommender.db.models import Channel, Video, psql
from youtube_recommender.db.models import psql
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import EDUCATIONAL_VIDEOS_PATH

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

s = get_session(psql)()

parser = argparse.ArgumentParser(description="create_educational_videos_dataset optional parameters")
parser.add_argument(
    "-s",
    "--save_feather",
    action="store_true",
    default=False,
    help="Save dataset to feather",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # stmt = select(Video).join(Channel).where(Video.is_educational).limit(10)
    stmt = """
        SELECT
            video.*,
            channel.name AS channel_name,
            channel.num_subscribers
        FROM
            video
            INNER JOIN channel ON channel.id = video.channel_id
        WHERE video.is_educational = 't'
        ORDER BY
            video.updated DESC
        LIMIT
            50000
    """

    videos = s.execute(stmt).mappings().fetchall()
    # df = pd.DataFrame([v.as_dict() for v in videos])
    df = pd.DataFrame(videos)

    # save to feather
    if args.save_feather:
        im.save_feather(df, EDUCATIONAL_VIDEOS_PATH, "educational_video")

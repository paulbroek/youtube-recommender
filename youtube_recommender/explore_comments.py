import argparse
import asyncio
import logging
import sys
from functools import partial
from itertools import chain
from multiprocessing import Pool
from typing import Any, Dict, Iterator, List

import jsonlines
import numpy as np
import pandas as pd
from rarc_utils.decorators import items_per_sec
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session
from youtube_comment_downloader.downloader import \
    YoutubeCommentDownloader  # type: ignore[import]
from youtube_recommender.data_methods import data_methods as dm
from youtube_recommender.db.helpers import get_video_ids_by_channel_ids
from youtube_recommender.db.models import psql
from youtube_recommender.settings import COMMENTS_FILE

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)

async_session = get_async_session(psql)

loop = asyncio.get_event_loop()

if __name__ == "__main__":
    data = []
    with jsonlines.open(COMMENTS_FILE) as reader:
        for obj in reader:
            data.append(obj)

    df = pd.DataFrame(df)

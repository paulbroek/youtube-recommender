"""top_videos.py.

Get top videos from materialized view
Save to .feather 
"""

import argparse
import logging
from youtube_recommender.io_methods import io_methods
from youtube_recommender.settings import VIDEOS_PATH
from youtube_recommender.utils.db_conn import load_db_table
from youtube_recommender.config.config import get_project_root
from rarc_utils.log import setup_logger, LOG_FMT

logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=LOG_FMT
)

# Project root
PROJECT_ROOT = get_project_root()

# Read database - PostgreSQL
VIEW: str = "top_videos"
LIMIT: int = 50_000
df = load_db_table(
    config_db="database.ini", query=f"SELECT * FROM {VIEW} LIMIT {LIMIT}"
)
print(df)

# Save as feather file
io_methods.save_feather(df, VIDEOS_PATH, "video")

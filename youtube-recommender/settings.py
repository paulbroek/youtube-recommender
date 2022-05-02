""" settings.py
	
general settings for youtube-recommender
"""

from pathlib import Path

__all__ = [
    "VIDEOS_PATH",
    "CAPTIONS_PATH",
]

DATA_DIR = Path("youtube-recommender/data")

VIDEOS_FILE = "top_videos.feather"
VIDEOS_PATH = DATA_DIR / VIDEOS_FILE

CAPTIONS_FILE = "captions.feather"
CAPTIONS_PATH = DATA_DIR / CAPTIONS_FILE

"""Settings.py, general settings for youtube-recommender."""

from pathlib import Path

__all__ = [
    "CONFIG_FILE",
    "VIDEOS_PATH",
    "CAPTIONS_PATH",
    "SPACY_MODEL",
]

######################
##### cfg paths ######
######################

CONFIG_FILE = "config.yaml"

######################
##### File paths #####
######################

# DATA_DIR = Path("youtube_recommender/data")
DATA_DIR = Path("/home/paul/repos/youtube-recommender/youtube_recommender/data")

VIDEOS_FILE = "top_videos.feather"
VIDEOS_PATH = DATA_DIR / VIDEOS_FILE

CAPTIONS_FILE = "captions.feather"
CAPTIONS_PATH = DATA_DIR / CAPTIONS_FILE

#################
##### SpaCy #####
#################

SPACY_MODEL = "en_core_web_sm"

#####################
##### Constants #####
#####################

# max hours ago for cache item to remain valid
PSQL_HOURS_AGO = 7 * 24
YOUTUBE_VIDEO_PREFIX = "https://www.youtube.com/watch?v="
YOUTUBE_CHANNEL_PREFIX = "https://www.youtube.com/channel/"

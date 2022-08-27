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
REPO_DIR = Path("/home/paul/repos/youtube-recommender/youtube_recommender")
DATA_DIR = REPO_DIR / "data"
EXPORT_DIR = REPO_DIR / "export"

VIDEOS_FILE = "top_videos.feather"
VIDEOS_PATH = DATA_DIR / VIDEOS_FILE

EDUCATIONAL_VIDEOS_FILE = "educational_videos.feather"
EDUCATIONAL_VIDEOS_PATH = DATA_DIR / EDUCATIONAL_VIDEOS_FILE
MODEL_PATH = EXPORT_DIR / "educational_video_descriptions.model"
TOPICS_PATH = EXPORT_DIR / "educational_video_descriptions.feather"

CAPTIONS_FILE = "captions.feather"
CAPTIONS_PATH = DATA_DIR / CAPTIONS_FILE

PYTUBE_VIDEOS_FILE = "pytube_videos.feather"
PYTUBE_VIDEOS_PATH = DATA_DIR / PYTUBE_VIDEOS_FILE

WATCH_HISTORY_JSON = DATA_DIR / "watch-history.json"
WATCH_HISTORY_FEATHER = DATA_DIR / "watch-history.feather"
SEARCH_HISTORY_JSON = DATA_DIR / "search-history.json"

CHAPTERS_JL_FILE = EXPORT_DIR / "chapters.jl"

COMMENTS_JL_FILE = EXPORT_DIR / "comments.jl"
COMMENTS_FEATHER_FILE = EXPORT_DIR / "comments.feather"
COMMENTS_PICKLE_FILE = EXPORT_DIR / "comments.pickle"

#################
##### SpaCy #####
#################

SPACY_MODEL = "en_core_web_sm"

#####################
##### Constants #####
#####################

# max hours ago for cache item to remain valid
PSQL_HOURS_AGO = 7 * 24
HOUR_LIMIT = 99_999_999
YOUTUBE_VIDEO_PREFIX = "https://www.youtube.com/watch?v="
YOUTUBE_CHANNEL_PREFIX = "https://www.youtube.com/channel/"

#############################
##### Scrape attributes #####
#############################

VIDEO_FIELDS = (
    "title",
    "channel_id",
    "channel_url",
    "description",
    "keywords",
    "length",
    "rating",
    "publish_date",
    "views",
    "video_id",
)

CHANNEL_FIELDS = (
    "title",
    "channel_id",
)

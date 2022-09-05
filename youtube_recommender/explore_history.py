"""explore_history.py.

Download search/watch history from Google Takeout
Load dataset and ask user to scrape missing channels / videos
Visualize what videos you watch most, per week / month, and by topic

How to get watch history from Google Takeout?
    -> https://takeout.google.com/settings/takeout → deselect all, select YouTube → deselect all, select Watch history → Select format, JSON, -> export to google drive
    -> next time you an click on "Manage your exports" and press "Create new export"

Todo:
    - Also use file `search-history.json`, can give more info of user's interests

Run:
    # load raw json dataset, directly from Google Takeout
    ipy explore_history.py -- -t json
    # load dataset with scraped YouTube channels using pytube
    ipy explore_history.py -- -t feather

    scrape channels for your watch history:
        df_watch = scrape_channels(df_watch)
"""

import argparse
import asyncio
import logging
from typing import Optional

import matplotlib.pyplot as plt  # type: ignore[import]
import pandas as pd
from pytube import YouTube  # type: ignore[import]
from pytube.exceptions import RegexMatchError  # type: ignore[import]
from rarc_utils.sqlalchemy_base import (get_async_session, get_session,
                                        load_config)
from tqdm import tqdm  # type: ignore[import]
from youtube_recommender import config as config_dir
from youtube_recommender.data_methods import data_methods as dm
from youtube_recommender.db.models import scrapeJob
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (SEARCH_HISTORY_JSON,
                                          WATCH_HISTORY_FEATHER,
                                          WATCH_HISTORY_JSON)

logger = logging.getLogger(__name__)

# use tqdm with df.progress_map()
tqdm.pandas()


def parse_iso_time(df: pd.DataFrame) -> pd.DataFrame:
    """Parse iso time to datetime."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["time"])
    df["datetime"] = df["datetime"].dt.tz_localize(None)
    df = df.set_index("datetime", drop=True)

    return df


def parse_watch_history(df: pd.DataFrame) -> pd.DataFrame:
    """Parse watch history."""
    df = df.dropna(subset=["titleUrl"])
    # extract video id
    df["video_id"] = df["titleUrl"].str.split("=").map(lambda x: x[-1])

    df = parse_iso_time(df)

    return df


def parse_search_history(df: pd.DataFrame) -> pd.DataFrame:
    """Parse search history."""
    df = df.dropna(subset=["titleUrl"])
    # extract search term
    df["search_term"] = df["title"].str.replace(r"^Searched for ", "")

    df = parse_iso_time(df)

    return df


def load_watch_history_json() -> pd.DataFrame:
    """Load watch history json."""
    df: pd.DataFrame = im.load_json(WATCH_HISTORY_JSON)
    df = parse_watch_history(df)

    return df


def load_search_history() -> pd.DataFrame:
    """Load search history."""
    df: pd.DataFrame = im.load_json(SEARCH_HISTORY_JSON)
    df = parse_search_history(df)

    return df


def load_watch_history_feather() -> pd.DataFrame:
    """Load watch history feather."""
    df: pd.DataFrame = pd.read_feather(WATCH_HISTORY_FEATHER)
    df = parse_watch_history(df)

    return df


def save_watch_history_feather(df: pd.DataFrame) -> None:
    """Save watch history."""
    df.reset_index().drop(["datetime"], axis=1).to_feather(WATCH_HISTORY_FEATHER)


def most_viewed_videos(df: pd.DataFrame) -> pd.DataFrame:
    """Compute most viewed videos."""
    vw: pd.DataFrame = (
        df.groupby("video_id")
        .agg(video_count=("video_id", "count"), title=("title", "last"))
        .sort_values("video_count", ascending=False)
    )
    return vw


def count_by_period(df: pd.DataFrame, freq="M", dropLastPeriod=True) -> pd.DataFrame:
    """Count by period, to see usage per period.

    dropLastPeriod:     drop last period, or it will impact the chart
    """
    vw: pd.DataFrame = df.groupby(pd.Grouper(freq=freq)).agg(count=("time", "count"))

    if dropLastPeriod:
        vw = vw.iloc[:-1].copy()

    return vw


def merge_datasets(
    dfw: pd.DataFrame, dfs: pd.DataFrame, freq="M", dropLastPeriod=True
) -> pd.DataFrame:
    """Merge watch and search datasets."""
    assert isinstance(dfs.index, pd.DatetimeIndex)
    assert isinstance(dfw.index, pd.DatetimeIndex)
    vw_search = count_by_period(dfs, freq=freq, dropLastPeriod=dropLastPeriod)
    vw_watch = count_by_period(dfw, freq=freq, dropLastPeriod=dropLastPeriod)
    # combine datasets
    merge = pd.merge(
        vw_watch,
        vw_search,
        how="inner",
        left_index=True,
        right_index=True,
        suffixes=["_watch", "_search"],
    )

    logger.info(f"merged datasets into {merge.shape[0]:,} rows")

    return merge


def plot_usage_over_time(df: pd.DataFrame, ax=None) -> None:
    """Plot usage over time."""
    df.plot(ax=ax)
    plt.show()


def create_pytube_object(url: str) -> Optional[YouTube]:
    """Create PyTube object."""
    res: Optional[YouTube] = None
    try:
        res = YouTube(url)
    except RegexMatchError:
        pass

    return res


def scrape_channels(df: pd.DataFrame):
    """Scrape channel_id, channel_url via youtube url."""
    df["yt"] = df["titleUrl"].map(create_pytube_object)
    df = df[~df['yt'].isna()].copy()
    pct_not_valid_url = df["yt"].isna().sum() / df.shape[0]
    logger.info(f"{pct_not_valid_url=:.1%}")
    # yt objects are only scraped when calling an attribute
    df["channel_id"] = df["yt"].progress_map(
        lambda x: x.channel_id if x is not None else None
    )
    df["channel_url"] = df["yt"].map(lambda x: x.channel_url if x is not None else None)
    df["channel_name"] = df["yt"].map(lambda x: x.channel_name if x is not None else None)

    del df["yt"]

    return df


def push_scrape_jobs(df: pd.DataFrame) -> None:
    """Create channels, and one scrapeJob per (new) channel."""
    # push channels first
    datad = loop.run_until_complete(dm.push_channels(df, async_session))

    df = df.dropna(subset=["channel_id"])
    df["scrapeJob"] = df.channel_id.map(lambda x: scrapeJob(channel_id=x))

    sjs = df["scrapeJob"].to_list()
    psession.add_all(sjs)
    psession.commit()

    # todo: push to db
    # todo: upsert nupdate, done?


parser = argparse.ArgumentParser(description="explore_history.py cli parameters")
parser.add_argument(
    "-t",
    "--file_type",
    type=str,
    default="json",
    help="dataset type to load: json / feather",
)
parser.add_argument(
    "--cfg_file",
    type=str,
    default="postgres.cfg",
    help="cfg file of db to push scrapeJobs to",
)
parser.add_argument(
    "-p",
    "--push_scrape_jobs",
    action="store_true",
    default=False,
    help="push channel_ids to db as scrapeJob",
)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    cli_args = parser.parse_args()

    psql = load_config(
        db_name="youtube",
        cfg_file=cli_args.cfg_file,
        config_dir=config_dir,
        starts_with=True,
    )
    psession = get_session(psql)()
    async_session = get_async_session(psql)

    if cli_args.file_type == "json":
        df_watch = load_watch_history_json()
    elif cli_args.file_type == "feather":
        df_watch = load_watch_history_feather()

    df_search = load_search_history()

    view = most_viewed_videos(df_watch)

    if cli_args.push_scrape_jobs:
        push_scrape_jobs(df_watch)

    # vw_search = count_by_period(df_search)
    # vw_watch = count_by_period(df_watch)
    # vw_search.plot(); plt.show()

    # df = merge_datasets(df_search, df_watch, freq="M"); plot_usage_over_time(df)

    # df_watch = scrape_channels(df_watch)

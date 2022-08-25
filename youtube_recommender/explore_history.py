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
    ipy explore_history.py

    scrape channels for your watch history:
        df_watch = scrape_channels(df_watch)
"""

import logging
from typing import Optional

import matplotlib.pyplot as plt  # type: ignore[import]
import pandas as pd
from pytube import YouTube  # type: ignore[import]
from pytube.exceptions import RegexMatchError  # type: ignore[import]
from tqdm import tqdm  # type: ignore[import]
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (SEARCH_HISTORY_FILE,
                                          WATCH_HISTORY_FILE)

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


def load_watch_history() -> pd.DataFrame:
    """Load watch history."""
    df: pd.DataFrame = im.load_json(WATCH_HISTORY_FILE)
    df = parse_watch_history(df)

    return df


def load_search_history() -> pd.DataFrame:
    """Load search history."""
    df: pd.DataFrame = im.load_json(SEARCH_HISTORY_FILE)
    df = parse_search_history(df)

    return df


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
    pct_not_valid_url = df["yt"].isna().sum() / df.shape[0]
    logger.info(f"{pct_not_valid_url=:.1%}")
    # yt objects are only scraped when calling an attribute
    df["channel_id"] = df["yt"].progress_map(
        lambda x: x.channel_id if x is not None else None
    )
    df["channel_url"] = df["yt"].map(lambda x: x.channel_url if x is not None else None)

    del df["yt"]

    return df


if __name__ == "__main__":
    df_watch = load_watch_history()
    df_search = load_search_history()

    view = most_viewed_videos(df_watch)

    # vw_search = count_by_period(df_search)
    # vw_watch = count_by_period(df_watch)
    # vw_search.plot(); plt.show()

    # df = merge_datasets(df_search, df_watch, freq="M"); plot_usage_over_time(df)

    # df_watch = scrape_channels(df_watch)

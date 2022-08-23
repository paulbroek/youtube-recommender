"""watch_history.py.

Download watch history from Google Takeout
Load dataset and ask user to scrape missing channels / videos
Visualize what videos you watch most, per week / month, and by topic

How to get watch history from Google Takeout?
    -> https://takeout.google.com/settings/takeout → deselect all, select YouTube → deselect all, select Watch history → Select format, JSON, -> export to google drive
    -> next time you an click on "Manage your exports" and press "Create new export"

Todo:
    - Also use file `search-history.json`, can give more info of user's interests
"""

import pandas as pd
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (SEARCH_HISTORY_FILE,
                                          WATCH_HISTORY_FILE)


def parse_watch_history(df: pd.DataFrame) -> pd.DataFrame:
    """Parse watch history."""
    df = df.dropna(subset=["titleUrl"])
    # extract video id
    df["video_id"] = df.titleUrl.str.split("=").map(lambda x: x[-1])

    return df


def group_by_most_viewed(df: pd.DataFrame) -> pd.DataFrame:
    """Group by most viewed."""
    view: pd.DataFrame = (
        df.groupby("video_id")
        .agg(video_count=("video_id", "count"), title=("title", "last"))
        .sort_values("video_count", ascending=False)
    )
    return view

def extract_channels():
    # scrape video first, and then channel
    raise NotImplementedError



if __name__ == "__main__":
    df = im.load_json(WATCH_HISTORY_FILE)

    df = parse_watch_history(df)

    view = group_by_most_viewed(df)

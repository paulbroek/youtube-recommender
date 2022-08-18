"""channel_lists.py.

Example visualization using Streamlit

Uses redis aiocache, so don't forget to run:

    cd ~/repos/youtube-recommender
    docker-compose up -d redis
"""
import asyncio
import logging

import numpy as np
import pandas as pd
import requests
import streamlit as st
from rarc_utils.misc import timeago_series
# from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, get_session
from youtube_recommender import config as config_dir
from youtube_recommender.db.db_methods import refresh_view
from youtube_recommender.db.helpers import (get_top_channels_with_comments,
                                            get_top_videos_by_channel_ids)
from youtube_recommender.db.models import load_config, psql

# todo: use customized logger with streamlit?
# LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"

# logger = setup_logger(
#     cmdLevel=logging.INFO, saveFile=0, savePandas=0, color=1, fmt=LOG_FMT
# )

logger = logging.getLogger(__name__)

psql = load_config(db_name="youtube", cfg_file="postgres.cfg", config_dir=config_dir)
async_session = get_async_session(psql)
psession = get_session(psql)()


def extract_channel_id(df: pd.DataFrame, channel_name: str) -> str:
    """Extract channel_id by channel_name."""
    assert len(df.channel_name) == len(df.channel_name.unique())
    cid: str = df[df.channel_name == channel_name]["channel_id"].values[0]

    return cid


def some_method():
    r = requests.get("https://www.nu.nl")
    logger.info("I ran")


async def main():

    df = await get_top_channels_with_comments(async_session, dropna=True)
    df["last_updated"] = pd.to_datetime(df.last_updated)
    df["last_updated_ago"] = pd.to_datetime(df.last_updated)

    df[["last_updated_ago"]] = df[["last_updated"]].apply(timeago_series, axis=0)

    title = st.text_input("Movie title", "Life of Brian")
    st.write("The current movie title is", title)

    """ 
    ## Top channelss
    """

    if st.button("Do request", on_click=some_method):
        st.write("i called api")
    else:
        st.write("goodbye")

    if st.button(
        "Refresh top channels view",
        on_click=refresh_view,
        args=("top_channels_with_comments",),
    ):
        st.write("refreshed view")
    else:
        st.write("Goodbye")

    st.dataframe(df)

    """ 
    ## Top videos by channel
    """

    # display channel_name (total_views)
    # channel_name_to_views = {"Traversy Media": 200}
    channel_views = dict(zip(df.channel_name, df.video_count))
    channel_updated_ago = dict(zip(df.channel_name, df.last_updated_ago))
    option = st.selectbox(
        "Select channel name:",
        df.channel_name.to_list(),
        format_func=lambda x: f"{x} ({channel_views[x]} videos, updated {channel_updated_ago[x]})",
    )

    channel_id = extract_channel_id(df, option)
    st.write("You selected:", option, ", channel_id: ", channel_id)
    rows = await get_top_videos_by_channel_ids(async_session, channel_ids=[channel_id])
    # dfc = pd.DataFrame(rows)
    dfc = rows
    dfc["minute_len"] = np.round(dfc["length"] / 60, 1)
    if not dfc.empty:
        st.dataframe(dfc.drop(["channel_id"], axis=1), width=1200)
    else:
        st.write("empty dataframe")

    # todo: show topics per channel
    # or select a custom list of videos, and extract topics, to see the performance of the model in action


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())

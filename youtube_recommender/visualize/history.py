"""history.py

Visualize YouTube watch and search history

Run:
    streamlit run history.py
"""

import logging

import streamlit as st
from youtube_recommender.explore_history import plot_usage_over_time
from youtube_recommender.io_methods import io_methods as im
from youtube_recommender.settings import (SEARCH_HISTORY_FILE,
                                          WATCH_HISTORY_FILE)

logger = logging.getLogger(__name__)

df_watch = im.load_json(WATCH_HISTORY_FILE)
df_search = im.load_json(SEARCH_HISTORY_FILE)

st.header("YouTube watch and search history")
option = st.selectbox("Select frequency:", ["M", "D", "W", "Q", "Y"])

logger.info(f"{df_watch=}")
logger.info(f"{option=}")

plot_usage_over_time(df_watch, df_search, freq=option, dropLastPeriod=True)

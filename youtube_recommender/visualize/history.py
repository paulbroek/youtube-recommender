"""history.py

Visualize YouTube watch and search history

Run:
    streamlit run history.py
"""

import logging

import matplotlib.pyplot as plt  # type: ignore[import]
import streamlit as st
from youtube_recommender.explore_history import (load_search_history,
                                                 load_watch_history,
                                                 merge_datasets,
                                                 plot_usage_over_time)

logger = logging.getLogger(__name__)

df_watch = load_watch_history()
df_search = load_search_history()

st.header("YouTube watch and search history")
option = st.selectbox("Select frequency:", ["M", "D", "W", "Q", "Y"])

logger.info(f"{option=}")

fig, ax = plt.subplots()

df = merge_datasets(df_watch, df_search, freq=option, dropLastPeriod=True)
plot_usage_over_time(df, ax=ax)

st.pyplot(fig)

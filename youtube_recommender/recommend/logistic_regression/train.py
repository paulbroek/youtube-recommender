#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import logging
import pandas as pd
from sklearn.pipeline import Pipeline


from youtube_recommender.io_methods import io_methods
from youtube_recommender.settings import VIDEOS_PATH
from rarc_utils.log import setup_logger, LOG_FMT

logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=LOG_FMT
)


# ### 0. Get data

# In[ ]:


df = io_methods.load_feather(VIDEOS_PATH, "video")


# ### 1. Define labels

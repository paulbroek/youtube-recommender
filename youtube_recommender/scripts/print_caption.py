"""print_caption.py.

print caption from CAPTIONS_PATH feather file
"""
import logging

import pandas as pd

from rarc_utils.log import LOG_FMT, setup_logger
from youtube_recommender.settings import CAPTIONS_PATH

logger = setup_logger(
    cmdLevel=logging.ERROR, saveFile=0, savePandas=0, color=1, fmt=LOG_FMT
)

data = pd.read_feather(CAPTIONS_PATH)

if len(data) > 1:
    logger.error("data contains more than one row, only printing first row")

# data.text.to_csv("/tmp/output.txt")
print(data.text[0])

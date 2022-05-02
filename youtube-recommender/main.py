#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:09:52 2020
@author: chrislovejoy
From: https://github.com/chris-lovejoy/YouTube-video-finder/

This module imports and calls the function to execute the API call
and print results to the console.
"""

import argparse
import logging

from rarc_utils.log import setup_logger

import video_finder as vf
from utils.misc import load_yaml
from settings import VIDEOS_PATH

log_fmt = "%(asctime)s - %(module)-14s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, fmt=log_fmt
)  # DEBUG

parser = argparse.ArgumentParser(description="Defining search parameters")
parser.add_argument(
    "search_terms", type=str, nargs="+", help="The terms to query. Can be multiple."
)
parser.add_argument(
    "--search-period", type=int, default=7, help="The number of days to search for."
)
parser.add_argument(
    "--save",
    action="store_true",
    default=False,
    help="Save results to ",
)
args = parser.parse_args()

config = load_yaml("./config.yaml")


if __name__ == "__main__":
    start_date_string = vf.get_start_date_string(args.search_period)
    res = vf.search_each_term(args.search_terms, config["api_key"], start_date_string)

    if args.save:
        df = res["top_videos"].reset_index()
        # extract video_id from url
        df['video_id'] = df['Video URL'].str.rsplit('?v=', n=1).str[1]
        df.to_feather(VIDEOS_PATH)
        logger.info(
            f"saved {len(df):,} top_videos metadata to {VIDEOS_PATH.as_posix()}"
        )

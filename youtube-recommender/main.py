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
from settings import DATA_DIR

log_fmt     = "%(asctime)s - %(module)-14s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  #name
logger      = setup_logger(cmdLevel=logging.INFO, saveFile=0, savePandas=1, fmt=log_fmt) # DEBUG

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
    help="Save results to json",
)
args = parser.parse_args()

config = load_yaml("./config.yaml")

VIDEOS_FILE = 'top_videos.feather'
VIDEOS_PATH = DATA_DIR / VIDEOS_FILE

if __name__ == "__main__":
    start_date_string = vf.get_start_date_string(args.search_period)
    res = vf.search_each_term(args.search_terms, config["api_key"], start_date_string)

    if args.save:
        df = res['top_videos'].reset_index()
        df.to_feather(VIDEOS_PATH)
        logger.info(f"saved {len(df):,} captions to {VIDEOS_PATH.as_posix()}")

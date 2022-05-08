#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Created on Wed Nov 11 16:09:52 2020.

@author: chrislovejoy
From: https://github.com/chris-lovejoy/YouTube-video-finder/

This module imports and calls the function to execute the API call
and print results to the console.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import uvloop
from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import get_async_session, get_session
from youtube_recommender import config as config_dir

from .data_methods import data_methods as dm
from .db.helpers import get_last_query_results, get_videos_by_query
from .db.models import psql
from .settings import CONFIG_FILE, VIDEOS_PATH
from .utils.misc import load_yaml
from .video_finder import (
    concat_dfs,
    get_start_date_string,
    save_feather,
    search_each_term,
)

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-20s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, color=1, fmt=log_fmt
)  # DEBUG

p = Path(config_dir.__file__)
cfgFile = p.with_name(CONFIG_FILE)

config = load_yaml(cfgFile)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()

async_session = get_async_session(psql)
psession = get_session(psql)()


parser = argparse.ArgumentParser(description="Defining search parameters")
parser.add_argument(
    "search_terms", type=str, nargs="+", help="The terms to query. Can be multiple."
)
parser.add_argument(
    "--search-period", type=int, default=365, help="The number of days to search for."
)
parser.add_argument(
    "--dryrun",
    action="store_true",
    default=False,
    help="only load modules, do not requests APIs",
)
parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    default=False,
    help="force to run query, do not use cache",
)
parser.add_argument(
    "--filter",
    action="store_true",
    default=False,
    help="filter non English titles from dataset using langid",
)
parser.add_argument(
    "-s",
    "--save",
    action="store_true",
    default=False,
    help="Save results to ",
)
parser.add_argument(
    "-p",
    "--push_db",
    action="store_true",
    default=False,
    help="push queryResult and Video rows to PostgreSQL`",
)

if __name__ == "__main__":
    args = parser.parse_args()
    exiting = False

    start_date_string = get_start_date_string(args.search_period)

    if args.dryrun:
        sys.exit()

    search_terms = set(args.search_terms)
    if not args.force:
        # before calling YouTube API, use PostgreSQL cache for search results younger than 7 days
        for query in args.search_terms:
            qrs = get_last_query_results(psession, query=query)  # maxHoursAgo=2
            if len(qrs) > 0:
                logger.info(
                    f"got cache results for {query=:<25}, dismissing it from search_terms"
                )
                # filter out the query
                search_terms.discard(query)

            psession.close()

    # todo: distinguish between search_terms from cache and others, combine results later. are df's of same shape?
    if len(search_terms) > 0:
        # res = search_each_term(search_terms, config["api_key"], start_date_string) # blocking code
        res = loop.run_until_complete(
            search_each_term(list(search_terms), config["api_key"], start_date_string)
        )
        df = res["top_videos"].reset_index(drop=True)

    else:
        # recreate dataframe for cached search terms
        # get dataframes per search query, combine them later
        dfs = []
        for query in args.search_terms:
            recs = loop.run_until_complete(get_videos_by_query(async_session, query))
            df_ = dm.create_df_from_cache(recs)
            dfs.append(df_)

        # combine dataframes
        df = concat_dfs(dfs)

        # logger.info("nothing to do")
        # sys.exit()
        # exiting = True

    if df.empty:
        logger.info("nothing to do")
        exiting = True

    if not exiting:
        if args.filter:
            df = dm.classify_language(df, "title")
            df = dm.keep_language(df, "en")

        # extract video_id and channel_id from respective urls
        df = df.pipe(dm.extract_video_id).pipe(dm.extract_channel_id)

        # save video metadata to feather file
        if args.save:
            save_feather(df, VIDEOS_PATH)

        if args.push_db and len(search_terms) > 0:

            res.pop("top_videos")
            query_dict = {}

            # push per query
            for query, df_ in res.items():
                df_ = df_.pipe(dm.extract_video_id).pipe(dm.extract_channel_id)

                datad = loop.run_until_complete(dm.push_videos(df_, async_session))
                # assert isinstance(datad, dict)
                query_dict[query] = datad["video"]

            psession.close()

            # save queryResults, but only if search terms where queried
            dm.push_query_results(query_dict, psession)  # search_terms,

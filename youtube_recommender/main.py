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
import sys
import logging
import asyncio
import uvloop

from rarc_utils.log import setup_logger
from rarc_utils.sqlalchemy_base import (
    get_async_session,
    get_session,
)

import video_finder as vf
import data_methods as dm
from db.models import Video, Channel, queryResult, psql
from db.helpers import create_many_items, get_last_query_results
from utils.misc import load_yaml
from settings import VIDEOS_PATH

log_fmt = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # name
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
    "--dryrun",
    action="store_true",
    default=False,
    help="only load modules, do not requests APIs",
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

    config = load_yaml("./config.yaml")

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()

    async_session = get_async_session(psql)
    psession = get_session(psql)()

    start_date_string = vf.get_start_date_string(args.search_period)

    if args.dryrun:
        sys.exit()

    search_terms = set(args.search_terms)
    # before calling YouTube API, use PostgreSQL cache for search results younger than 7 days
    for query in args.search_terms:
        qrs = get_last_query_results(
            psession, query=query, model=queryResult
        )  # maxHoursAgo=2
        if len(qrs) > 0:
            logger.info(
                f"got cache results for {query=:<25}, dismissing it from search_terms"
            )
            # filter out the query
            search_terms.discard(query)

        psession.close()

    # todo: recreate dataframe for cached search terms

    if len(search_terms) > 0:
        # res = vf.search_each_term(search_terms, config["api_key"], start_date_string) # blocking code
        res = loop.run_until_complete(
            vf.search_each_term(
                list(search_terms), config["api_key"], start_date_string
            )
        )
        df = res["top_videos"].reset_index(drop=True)

    else:
        logger.info("nothing to do")
        sys.exit()

    if args.filter:
        df = dm.classify_language(df, "Title")
        df = dm.keep_language(df, "en")

    # extract video_id and channel_id from respective urls
    df = df.pipe(dm.extract_video_id).pipe(dm.extract_channel_id)

    # save video metadata to feather file
    if args.save:
        vf.save_feather(df, VIDEOS_PATH)

    if args.push_db:
        channel_recs = dm.make_channel_recs(df)

        # create channels from same dataset
        channels_dict = loop.run_until_complete(
            create_many_items(
                async_session, Channel, channel_recs, nameAttr="id", returnExisting=True
            )
        )

        # map the new channels into vdf
        df["channel"] = df["channel_id"].map(channels_dict)

        video_recs = dm.make_video_recs(df)

        videos_dict = loop.run_until_complete(
            create_many_items(
                async_session, Video, video_recs, nameAttr="id", returnExisting=True
            )
        )

        # save queryResults
        for query in args.search_terms:
            qr = queryResult(query=query, videos=list(videos_dict.values()))
            psession.add(qr)
            psession.commit()

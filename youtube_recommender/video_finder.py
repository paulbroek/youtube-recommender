#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:09:52 2020
@author: chrislovejoy
From: 
    https://github.com/chris-lovejoy/YouTube-video-finder/
"""

from typing import List, Union, Dict
import logging
from datetime import datetime, timedelta
from time import time
from pathlib import Path
import asyncio

import pandas as pd

from apiclient.discovery import build

logger = logging.getLogger(__name__)

def get_start_date_string(search_period_days: int) -> str:
    """Returns string for date at start of search period."""

    search_start_date = datetime.today() - timedelta(search_period_days)
    date_string = datetime(year=search_start_date.year,month=search_start_date.month,
                           day=search_start_date.day).strftime('%Y-%m-%dT%H:%M:%SZ')
    return date_string


async def search_each_term(search_terms: Union[str, List[str]], api_key, uploaded_since,
                        views_threshold=5000, num_to_print=5) -> Dict[str, pd.DataFrame]:
    """Uses search term list to execute API calls and print results."""

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    t0 = time()

    # list_of_dfs = find_all_terms(search_terms, api_key, uploaded_since, views_threshold)
    list_of_dfs  = await afind_all_terms(search_terms, api_key, uploaded_since, views_threshold)

    elapsed = time() - t0

    # 1 - concatenate them all
    full_df = pd.concat((list_of_dfs), axis=0)
    full_df = full_df.sort_values(['Custom_Score'], ascending=[0])
    logger.debug("THE TOP VIDEOS OVERALL ARE:")
    print_top_videos(full_df, num_to_print)
    logger.debug("==========================\n")

    # 2 - in total
    for index, _ in enumerate(search_terms):
        results_df = list_of_dfs[index]
        logger.debug("THE TOP VIDEOS FOR SEARCH TERM '{}':".format(search_terms[index]))
        print_top_videos(results_df, num_to_print)

    results_df_dict = dict(zip(search_terms, list_of_dfs))
    results_df_dict['top_videos'] = full_df

    logger.info(f"got {len(full_df):,} rows in {elapsed:.2f} secs")

    return results_df_dict


def find_videos(search_terms, api_key, views_threshold, uploaded_since):
    """Calls other functions (below) to find results and populate dataframe."""

    # Initialise results dataframe
    dataframe = pd.DataFrame(columns=('Title', 'Video URL', 'Custom_Score',
                            'Views', 'Description', 'Channel Name','Num_subscribers',
                            'View-Subscriber Ratio','Channel URL'))

    # Run search
    search_results, youtube_api = search_api(search_terms, api_key,
                                                        uploaded_since)

    results_df = populate_dataframe(search_results, youtube_api, dataframe,
                                                        views_threshold)

    results_df = results_df.sort_values(['Custom_Score'], ascending=[0])

    return results_df

def find_all_terms(search_terms, api_key, uploaded_since, views_threshold):

    list_of_dfs = []
    for index, _ in enumerate(search_terms):
        df = find_videos(search_terms[index], api_key, views_threshold=views_threshold,
                         uploaded_since = uploaded_since)
        
        list_of_dfs.append(df)

    return list_of_dfs

async def afind_all_terms(search_terms, api_key, uploaded_since, views_threshold):
    """speeding up downloading of captions by running them concurrently
    usage:
        results_df_dict = loop.run_until_complete(vf.afind_all_terms(search_terms, api_key, uploaded_since, views_threshold))
    """

    loop = asyncio.get_running_loop()

    cors = [
        loop.run_in_executor(None, find_videos, search_term, api_key, views_threshold, uploaded_since)
        for search_term in search_terms
    ]

    list_of_dfs = await asyncio.gather(*cors)
    return list_of_dfs

def search_api(search_terms, api_key, uploaded_since):
    """Executes search through API and returns result."""

    # Initialise API call
    youtube_api = build('youtube', 'v3', developerKey = api_key)

    # Make the search
    # update by paul: I set relevanceLanguage to 'en', but it will still return other language videos
    # filter them out later by classifying the related caption
    results = youtube_api.search().list(q=search_terms, part='snippet',
                                type='video', order='viewCount', maxResults=50,
                                publishedAfter=uploaded_since, relevanceLanguage='en', ).execute()

    return results, youtube_api


def populate_dataframe(results, youtube_api, df, views_threshold) -> pd.DataFrame:
    """Extracts relevant information and puts into dataframe"""
    # Loop over search results and add key information to dataframe
    i = 1
    for item in results['items']:
        viewcount = find_viewcount(item, youtube_api)
        if viewcount > views_threshold:
            title = find_title(item)
            video_url = find_video_url(item)
            description = find_description(item, youtube_api)
            channel_url = find_channel_url(item)
            channel_id = find_channel_id(item)
            channel_name = find_channel_title(channel_id, youtube_api)
            num_subs = find_num_subscribers(channel_id, youtube_api)
            ratio = view_to_sub_ratio(viewcount, num_subs)
            days_since_published = how_old(item)
            score = custom_score(viewcount, ratio, days_since_published)
            df.loc[i] = [title, video_url, score, viewcount, description, channel_name,\
                                    num_subs, ratio, channel_url]
        i += 1
    return df


def print_top_videos(df, num_to_print) -> None:
    """Prints top videos to console, with details and link to video."""
    if len(df) < num_to_print:
        num_to_print = len(df)
    if num_to_print == 0:
        logger.debug("No video results found")
    else:
        for i in range(num_to_print):
            video = df.iloc[i]
            title = video['Title']
            views = video['Views']
            subs = video['Num_subscribers']
            link = video['Video URL']
            logger.debug("Video #{}:\nThe video '{}' has {} views, from a channel \
with {} subscribers and can be viewed here: {}\n"\
                                        .format(i+1, title, views, subs, link))
            logger.debug("==========================\n")

def save_feather(df: pd.DataFrame, videos_path) -> None:
    assert isinstance(videos_path, Path)

    df.to_feather(videos_path)
    logger.info(
        f"saved {len(df):,} top_videos metadata to {videos_path.as_posix()}"
    )


## ======================================================================= ##
## ====== SERIES OF FUNCTIONS TO PARSE KEY INFORMATION ABOUT VIDEOS ====== ##
## ======================================================================= ##

def find_title(item):
    title = item['snippet']['title']
    return title

def find_video_url(item):
    video_id = item['id']['videoId']
    video_url = "https://www.youtube.com/watch?v=" + video_id
    return video_url

def find_viewcount(item, youtube):
    video_id = item['id']['videoId']
    video_statistics = youtube.videos().list(id=video_id,
                                        part='statistics').execute()
    # logger.info(f"{video_id=} {video_statistics['items'][0]['statistics']=}")
    # videos with comments turned off will not return viewCount
    if 'viewCount' not in video_statistics['items'][0]['statistics']:
        viewcount = 0 
    else:
        viewcount = int(video_statistics['items'][0]['statistics']['viewCount'])
    return viewcount

def find_description(item, youtube):
    """ added by paul """
    video_id = item['id']['videoId']
    video_statistics = youtube.videos().list(id=video_id,
                                        part='snippet').execute()
    description = video_statistics['items'][0]['snippet']['description']
    return description

def find_channel_id(item):
    channel_id = item['snippet']['channelId']
    return channel_id

def find_channel_url(item):
    channel_id = item['snippet']['channelId']
    channel_url = "https://www.youtube.com/channel/" + channel_id
    return channel_url

def find_channel_title(channel_id, youtube):
    channel_search = youtube.channels().list(id=channel_id,
                                            part='brandingSettings').execute()
    channel_name = channel_search['items'][0]\
                                    ['brandingSettings']['channel']['title']
    return channel_name

def find_num_subscribers(channel_id, youtube):
    subs_search = youtube.channels().list(id=channel_id,
                                            part='statistics').execute()
    if subs_search['items'][0]['statistics']['hiddenSubscriberCount']:
        num_subscribers = 1000000
    else:
        num_subscribers = int(subs_search['items'][0]\
                                    ['statistics']['subscriberCount'])
    return num_subscribers

def view_to_sub_ratio(viewcount, num_subscribers):
    if num_subscribers == 0:
        return 0
    else:
        ratio = viewcount / num_subscribers
        return ratio

def how_old(item):
    when_published = item['snippet']['publishedAt']
    when_published_datetime_object = datetime.strptime(when_published,
                                                        '%Y-%m-%dT%H:%M:%SZ')
    today_date = datetime.today()
    days_since_published = int((today_date - when_published_datetime_object).days)
    if days_since_published == 0:
        days_since_published = 1
    return days_since_published

def custom_score(viewcount, ratio, days_since_published):
    ratio = min(ratio, 5)
    score = (viewcount * ratio) / days_since_published
    return score

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:09:52 2020.

@author: chrislovejoy
From:
    https://github.com/chris-lovejoy/YouTube-video-finder/
"""
import asyncio
import logging
from datetime import datetime, timedelta
from os import path
from pathlib import Path
from time import time
from typing import Any, Dict, List, Union

import pandas as pd
from apiclient.discovery import build  # type: ignore[import]

logger = logging.getLogger(__name__)

RESULT_PER_PAGE = 50
MAX_RESULTS = 100

__all__ = [
    "get_start_date_string",
    "search_each_term",
    "load_feather",
    "save_feather",
]


# ======================================================================= #
# ======                       PUBLIC METHODS                      ====== #
# ======================================================================= #


def get_start_date_string(search_period_days: int) -> str:
    """Return string for date at start of search period."""
    search_start_date = datetime.today() - timedelta(search_period_days)
    date_string = datetime(
        year=search_start_date.year,
        month=search_start_date.month,
        day=search_start_date.day,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return date_string


async def search_each_term(
    search_terms: Union[str, List[str]],
    api_key,
    uploaded_since,
    views_threshold=5000,
    num_to_print=5,
    n=MAX_RESULTS,
) -> Dict[str, pd.DataFrame]:
    """Use search term list to execute API calls and print results."""
    if isinstance(search_terms, str):
        search_terms = [search_terms]

    t0 = time()

    # list_of_dfs = _find_all_terms(search_terms, api_key, uploaded_since, views_threshold)
    list_of_dfs = await _afind_all_terms(
        search_terms, api_key, uploaded_since, views_threshold, n=n
    )

    elapsed = time() - t0

    # 1 - concatenate them all
    full_df = concat_dfs(list_of_dfs)
    logger.debug("THE TOP VIDEOS OVERALL ARE:")
    _print_top_videos(full_df, num_to_print)
    logger.debug("==========================\n")

    # 2 - in total
    for index, _ in enumerate(search_terms):
        results_df = list_of_dfs[index]
        logger.debug("THE TOP VIDEOS FOR SEARCH TERM '{}':".format(search_terms[index]))
        _print_top_videos(results_df, num_to_print)

    results_df_dict = dict(zip(search_terms, list_of_dfs))
    results_df_dict["top_videos"] = full_df

    logger.info(f"got {len(full_df):,} rows in {elapsed:.2f} secs")

    return results_df_dict


def concat_dfs(list_of_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    if len(list_of_dfs) == 0:
        return pd.DataFrame()

    full_df = pd.concat((list_of_dfs), axis=0)
    full_df = full_df.sort_values(["custom_score"], ascending=[0])

    return full_df


def load_feather(videos_path: Path) -> pd.DataFrame:
    """Load top_videos metadata dataframe from feather."""
    # check if file exists, or warn user to run main.py first
    assert path.exists(
        videos_path
    ), f"{videos_path.as_posix()} does not exist, create it by running e.g.: \
        `ipy -m youtube_recommender -- 'robbins' 'earth' --save`"
    vdf = pd.read_feather(videos_path)

    return vdf


def save_feather(df: pd.DataFrame, videos_path: Path) -> None:
    """Save video metadata dataframe to feather."""
    assert isinstance(df, pd.DataFrame)
    assert isinstance(videos_path, Path)

    df.to_feather(videos_path)
    logger.info(f"saved {len(df):,} video metadatas to {videos_path.as_posix()}")


# ======================================================================= #
# ======                       PRIVATE METHODS                     ====== #
# ======================================================================= #


def _find_videos(search_terms, api_key, views_threshold, uploaded_since, n=MAX_RESULTS):
    """Call other functions (below) to find results and populate dataframe."""
    # Initialise results dataframe
    dataframe = pd.DataFrame(
        columns=(
            "title",
            "video_url",
            "custom_score",
            "views",
            "description",
            "channel_name",
            "num_subscribers",
            "view_subscriber_atio",
            "channel_url",
        )
    )

    # Run search
    search_results, youtube_api = _search_api(
        search_terms, api_key, uploaded_since, n=n
    )

    # raise SystemError("debugging")

    results_df = _populate_dataframe(
        search_results, youtube_api, dataframe, views_threshold
    )

    results_df = results_df.sort_values(["custom_score"], ascending=[0])

    return results_df


def _find_all_terms(search_terms: List[str], api_key, uploaded_since, views_threshold):
    """Find all terms in search terms."""
    list_of_dfs = []
    for index, _ in enumerate(search_terms):
        df = _find_videos(
            search_terms[index],
            api_key,
            views_threshold=views_threshold,
            uploaded_since=uploaded_since,
        )

        list_of_dfs.append(df)

    return list_of_dfs


async def _afind_all_terms(
    search_terms: List[str], api_key, uploaded_since, views_threshold, n=MAX_RESULTS
):
    """Speed up downloading of captions by running them concurrently.

    usage:
        results_df_dict = loop.run_until_complete(vf.afind_all_terms(search_terms, api_key, uploaded_since, views_threshold))
    """
    loop = asyncio.get_running_loop()

    cors = [
        loop.run_in_executor(
            None, _find_videos, search_term, api_key, views_threshold, uploaded_since, n
        )
        for search_term in search_terms
    ]

    list_of_dfs = await asyncio.gather(*cors)
    return list_of_dfs


def _search_api(search_terms: List[str], api_key, uploaded_since, n=300):
    """Execute search through API and returns result."""
    # Initialise API call
    youtube_api = build("youtube", "v3", developerKey=api_key)

    # Make the search
    # update by paul: I set relevanceLanguage to 'en', but it will still return other language videos
    # filter them out later by classifying the related caption
    # keep polling API, until maxn is reached
    niter = 0
    search_response: Dict[str, Any] = {"nextPageToken": None, "items": []}
    nextPageToken = search_response.get("nextPageToken")
    while (niter == 0 or "nextPageToken" in search_response) and len(
        search_response["items"]
    ) < n:

        nextPage = (
            youtube_api.search()
            .list(
                q=search_terms,
                part="snippet",
                type="video",
                order="viewCount",
                maxResults=RESULT_PER_PAGE,
                publishedAfter=uploaded_since,
                pageToken=nextPageToken,
                relevanceLanguage="en",
            )
            .execute()
        )

        search_response["items"] += nextPage["items"]

        niter += 1

        # print(f"{niter=}")

        if "nextPageToken" not in nextPage:
            search_response.pop("nextPageToken", None)
        else:
            nextPageToken = nextPage["nextPageToken"]

    return search_response, youtube_api


def _populate_dataframe(results, youtube_api, df, views_threshold) -> pd.DataFrame:
    """Extract relevant information and put it into dataframe."""
    # Loop over search results and add key information to dataframe
    i = 1
    for item in results["items"]:
        viewcount = _find_viewcount(item, youtube_api)
        if viewcount > views_threshold:
            title = _find_title(item)
            video_url = _find_video_url(item)
            description = _find_description(item, youtube_api)
            channel_url = _find_channel_url(item)
            channel_id = _find_channel_id(item)
            channel_name = _find_channel_title(channel_id, youtube_api)
            num_subs = _find_num_subscribers(channel_id, youtube_api)
            ratio = _view_to_sub_ratio(viewcount, num_subs)
            days_since_published = _how_old(item)
            score = _custom_score(viewcount, ratio, days_since_published)
            df.loc[i] = [
                title,
                video_url,
                score,
                viewcount,
                description,
                channel_name,
                num_subs,
                ratio,
                channel_url,
            ]
        i += 1
    return df


def _print_top_videos(df, num_to_print) -> None:
    """Print top videos to console, with details and link to video."""
    if len(df) < num_to_print:
        num_to_print = len(df)
    if num_to_print == 0:
        logger.debug("No video results found")
    else:
        for i in range(num_to_print):
            video = df.iloc[i]
            title = video["title"]
            views = video["views"]
            subs = video["num_subscribers"]
            link = video["video_url"]
            logger.debug(
                "Video #{}:\nThe video '{}' has {} views, from a channel \
                with {} subscribers and can be viewed here: {}\n".format(
                    i + 1, title, views, subs, link
                )
            )
            logger.debug("==========================\n")


# ======================================================================= #
# ====== SERIES OF FUNCTIONS TO PARSE KEY INFORMATION ABOUT VIDEOS ====== #
# ======================================================================= #


def _find_title(item):
    title = item["snippet"]["title"]
    return title


def _find_video_url(item):
    video_id = item["id"]["videoId"]
    video_url = "https://www.youtube.com/watch?v=" + video_id
    return video_url


def _find_viewcount(item, youtube):
    video_id = item["id"]["videoId"]
    video_statistics = youtube.videos().list(id=video_id, part="statistics").execute()
    # logger.info(f"{video_id=} {video_statistics['items'][0]['statistics']=}")
    # videos with comments turned off will not return viewCount
    if "viewCount" not in video_statistics["items"][0]["statistics"]:
        viewcount = 0
    else:
        viewcount = int(video_statistics["items"][0]["statistics"]["viewCount"])
    return viewcount


def _find_description(item, youtube):
    video_id = item["id"]["videoId"]
    video_statistics = youtube.videos().list(id=video_id, part="snippet").execute()
    description = video_statistics["items"][0]["snippet"]["description"]
    return description


def _find_channel_id(item):
    channel_id = item["snippet"]["channelId"]
    return channel_id


def _find_channel_url(item):
    channel_id = item["snippet"]["channelId"]
    channel_url = "https://www.youtube.com/channel/" + channel_id
    return channel_url


def _find_channel_title(channel_id, youtube):
    channel_search = (
        youtube.channels().list(id=channel_id, part="brandingSettings").execute()
    )
    channel_name = channel_search["items"][0]["brandingSettings"]["channel"]["title"]
    return channel_name


def _find_num_subscribers(channel_id, youtube):
    subs_search = youtube.channels().list(id=channel_id, part="statistics").execute()
    if subs_search["items"][0]["statistics"]["hiddenSubscriberCount"]:
        num_subscribers = 1000000
    else:
        num_subscribers = int(subs_search["items"][0]["statistics"]["subscriberCount"])
    return num_subscribers


def _view_to_sub_ratio(viewcount, num_subscribers):
    if num_subscribers == 0:
        return 0
    # else:
    ratio = viewcount / num_subscribers
    return ratio


def _how_old(item):
    when_published = item["snippet"]["publishedAt"]
    when_published_datetime_object = datetime.strptime(
        when_published, "%Y-%m-%dT%H:%M:%SZ"
    )
    today_date = datetime.today()
    days_since_published = int((today_date - when_published_datetime_object).days)
    if days_since_published == 0:
        days_since_published = 1
    return days_since_published


def _custom_score(viewcount, ratio, days_since_published):
    ratio = min(ratio, 5)
    score = (viewcount * ratio) / days_since_published
    return score

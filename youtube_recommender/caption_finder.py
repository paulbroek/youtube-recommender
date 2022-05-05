#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find and download captions from YouTube API
"""

from typing import List, Dict, Any, Optional  # , Union
from os import path
from pathlib import Path
import logging
import asyncio

import pandas as pd

from apiclient.discovery import build
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

import data_methods as dm

logger = logging.getLogger(__name__)


# def search_each_video(
#     search_terms: Union[str, List[str]], api_key
# ) -> Dict[str, pd.DataFrame]:
#     """search each video for captions"""

#     pass


def list_captions(video_id: str, api_key: str):
    """Executes captions search through API and returns result."""

    # Initialise API call
    youtube_api = build("youtube", "v3", developerKey=api_key)

    results = youtube_api.captions().list(part="snippet", videoId=video_id).execute()

    return results, youtube_api


def download_caption(caption_id: str, youtube_api, tfmt: str):
    """download caption using YouTube API
    Caution: requires OAuth credentials, cannot fetch caption for other user's videos
    """
    subtitle = youtube_api.captions().download(id=caption_id, tfmt=tfmt).execute()

    print("First line of caption track: %s" % (subtitle))

    return subtitle


def download_caption_v2(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """download caption using youtube_transcript_api"""

    captions: Optional[List[Dict[str, Any]]] = None

    try:
        captions = YouTubeTranscriptApi.get_transcript(video_id)
    except NoTranscriptFound:
        logger.error(
            f"cannot find caption for {video_id=}, probably not an english video, dismissing it"
        )
    except TranscriptsDisabled:
        logger.error(f"captions are disabled for {video_id=}, dismissing it")

    if captions is not None:
        return captions_to_dict(captions, video_id)

    return captions


def download_captions(video_ids: List[str]) -> List[Dict[str, Any]]:
    """download captions in blocking way
    usage:
        captions = cf.download_captions(video_ids)
    """

    res = [download_caption_v2(video_id) for video_id in video_ids]
    return list(filter(None, res))


async def adownload_captions(video_ids: List[str]) -> List[Dict[str, Any]]:
    """speeding up downloading of captions by running them concurrently
    usage:
        captions = loop.run_until_complete(cf.adownload_captions(video_ids))
    """

    loop = asyncio.get_running_loop()

    cors = [
        loop.run_in_executor(None, download_caption_v2, video_id)
        for video_id in video_ids
    ]

    captions = await asyncio.gather(*cors)
    return list(filter(None, captions))


def captions_to_dict(captions, video_id) -> dict:
    return dict(text=captions_to_str(captions, sep=", "), video_id=video_id)


def captions_to_df(captions: List[Dict[str, Any]], classify_lang=True) -> pd.DataFrame:
    df = pd.DataFrame(captions)
    assert "text" in df.columns
    assert "video_id" in df.columns
    df["text_len"] = df["text"].map(len)

    # can be removed, since download_captions automatically dismisses non-english captions and therefore videos?
    if classify_lang:
        df = dm.classify_language(df, "text")

    return df


def captions_to_str(captions: List[Dict[str, Any]], sep=", ") -> str:
    """join caption strs into one str"""

    assert len(captions) > 0
    texts = [t["text"] for t in captions]

    return sep.join(texts)


def load_feather(videos_path) -> pd.DataFrame:

    # check if file exists, or warn user to run main.py first
    assert path.exists(
        videos_path
    ), f"{videos_path.as_posix()} does not exist, create it by running e.g.: `ipy youtube-recommender/main.py -- 'robbins' 'earth' --save`"
    vdf = pd.read_feather(videos_path)

    return vdf

def save_feather(df: pd.DataFrame, captions_path) -> None:
    assert isinstance(captions_path, Path)
    
    df.to_feather(captions_path)
    logger.info(f"saved {len(df):,} captions to {captions_path.as_posix()}")

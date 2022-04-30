#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find and download captions from YouTube API
"""

from typing import List, Dict, Any #, Union
import logging

# Load dependencies
# from datetime import datetime, timedelta
# import pandas as pd
from apiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

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

    subtitle = youtube_api.captions().download(id=caption_id, tfmt=tfmt).execute()

    print("First line of caption track: %s" % (subtitle))

    return subtitle

def download_caption2(video_id: str) -> List[Dict[str, Any]]:

    captions  = YouTubeTranscriptApi.get_transcript(video_id)

    return captions

def download_captions(video_ids: List[str]) -> Dict[str, str]:
    res = dict()
    for video_id in video_ids:
        res[video_id] = download_caption2(video_id)
        res[video_id] = captions_to_str(res[video_id], sep=', ')

    return res

def captions_to_str(captions: List[Dict[str, Any]], sep=', ') -> str:
    """join caption strs into one str"""

    assert len(captions) > 0
    texts = [t['text'] for t in captions]

    return sep.join(texts)

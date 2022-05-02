#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find and download captions from YouTube API
"""

from typing import List, Dict, Any  # , Union
import logging

# Load dependencies
# from datetime import datetime, timedelta
import pandas as pd
from yapic import json

import langid
from apiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

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
    """download caption using YouTube APi
    Caution: requires OAuth credentials, cannot fetch caption for other user's videos
    """
    subtitle = youtube_api.captions().download(id=caption_id, tfmt=tfmt).execute()

    print("First line of caption track: %s" % (subtitle))

    return subtitle


def download_caption_v2(video_id: str) -> List[Dict[str, Any]]:
    """download caption using youtube_transcript_api"""
    captions = YouTubeTranscriptApi.get_transcript(video_id)

    return captions


def download_captions(video_ids: List[str]) -> List[Dict[str, Any]]:
    res = []
    for video_id in video_ids:
        try:
            captions: List[Dict[str, Any]] = download_caption_v2(video_id)
        except NoTranscriptFound:
            logger.error(f"cannot find caption for {video_id=}, probably not an english video, dismissing it")
            continue
        except TranscriptsDisabled:
            logger.error(f"captions are disabled for {video_id=}, dismissing it")
            continue

        row = dict(text=captions_to_str(captions, sep=", "), video_id=video_id)
        res.append(row)

    return res


def captions_to_df(captions: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(captions)
    assert "text" in df.columns
    assert "video_id" in df.columns
    df["text_len"] = df["text"].map(len)

    # todo: can be removed, since download_captions automatically dismisses non-english captions and therefore videos?
    df["language_cl"] = df["text"].map(langid.classify)
    df["language_cl"] = df["language_cl"].map(json.dumps)
    # todo: combine youtube api metadata with captions data
    # or use separate method for this?

    return df


def captions_to_str(captions: List[Dict[str, Any]], sep=", ") -> str:
    """join caption strs into one str"""

    assert len(captions) > 0
    texts = [t["text"] for t in captions]

    return sep.join(texts)

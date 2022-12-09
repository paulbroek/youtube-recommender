#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find and download captions from YouTube API."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from apiclient.discovery import build  # type: ignore[import]
from youtube_transcript_api import NoTranscriptFound  # type: ignore[import]
from youtube_transcript_api import TranscriptsDisabled, YouTubeTranscriptApi

from .core.types import CaptionId, VideoId
from .data_methods import data_methods as dm

logger = logging.getLogger(__name__)


# ======================================================================= #
# ======                       PUBLIC METHODS                      ====== #
# ======================================================================= #


def list_captions(video_id: VideoId, api_key: str):
    """Execute captions search through API and returns result."""
    # Initialise API call
    youtube_api = build("youtube", "v3", developerKey=api_key)

    results = youtube_api.captions().list(part="snippet", videoId=video_id).execute()

    return results, youtube_api


def download_caption(caption_id: CaptionId, youtube_api, tfmt: str):
    """Download caption using YouTube API.

    Caution: requires OAuth credentials, cannot fetch caption for other user's videos
    """
    subtitle = youtube_api.captions().download(id=caption_id, tfmt=tfmt).execute()

    print("First line of caption track: %s" % (subtitle))

    return subtitle


def download_captions(video_ids: List[VideoId]) -> List[Dict[str, Any]]:
    """Download captions in blocking way.

    usage:
        captions = cf.download_captions(video_ids)
    """
    res = [download_caption_v2(video_id) for video_id in video_ids]
    return list(filter(None, res))


def download_caption_v2(
    video_id: VideoId, withStartTimes: bool
) -> Optional[Dict[str, Any]]:
    """Download caption using youtube_transcript_api."""
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
        # TODO: do not simply concatenate strings, you lose the `start` and `duration` data
        return _captions_to_dict(captions, video_id, withStartTimes=withStartTimes)

    return captions


async def adownload_captions(
    video_ids: List[VideoId], withStartTimes=False
) -> List[Dict[str, Any]]:
    """Speed up downloading of captions by running them concurrently.

    usage:
        captions = loop.run_until_complete(cf.adownload_captions(video_ids))
    """
    loop = asyncio.get_running_loop()

    cors = [
        loop.run_in_executor(None, download_caption_v2, video_id, withStartTimes)
        for video_id in video_ids
    ]

    captions = await asyncio.gather(*cors)
    return list(filter(None, captions))


def save_feather(df: pd.DataFrame, captions_path: Path) -> None:
    """Save captions dataframe to feather."""
    assert isinstance(captions_path, Path)

    df.to_feather(captions_path)
    logger.info(f"saved {len(df):,} captions to {captions_path.as_posix()}")


def select_video_ids(df: pd.DataFrame, n=0) -> List[VideoId]:
    """Select video_ids from dataframe, optionally select first `n` rows."""
    assert isinstance(n, int)
    video_ids = df.video_id.astype(str).to_list()
    if n > 0:
        video_ids = video_ids[:n]

    logger.info(f"select {len(video_ids):,} video metadata rows")

    return video_ids


def captions_to_df(captions: List[Dict[str, Any]], classify_lang=True) -> pd.DataFrame:
    """Parse list of captions to Pandas DataFrame."""
    df = pd.DataFrame(captions)
    if df.empty:
        return df
    assert "text" in df.columns
    assert "video_id" in df.columns
    df["text_len"] = df["text"].map(len)

    # download_captions automatically dismisses non-english captions and therefore videos?
    # so can be removed?
    if classify_lang:
        df = dm.classify_language(df, "text")

    return df


# ======================================================================= #
# ======                       PRIVATE METHODS                     ====== #
# ======================================================================= #


def _captions_to_dict(
    captions: List[Dict[str, Any]], video_id: VideoId, withStartTimes=False
) -> Dict[str, Any]:
    return dict(
        text=_captions_to_str(captions, sep=", ", withStartTimes=withStartTimes),
        video_id=video_id,
    )


def _captions_to_str(
    captions: List[Dict[str, Any]], sep=", ", withStartTimes=False
) -> str:
    """Join caption strs into one str.

    withStartTimes:
        include startTimes, like
    """
    text: str = ""
    assert len(captions) > 0

    # TODO: or add a heuristic to decrease the number of `start` placeholders
    if withStartTimes:
        for t in captions:
            text += f"[{t['start']}]\n"
            text += f"{t['text']}\n"

    else:
        texts = [t["text"] for t in captions]
        text = str(sep.join(texts))

    return text

"""data_methods.py, contains methods for working with dataframes."""

import logging
import traceback
from operator import itemgetter
from typing import Dict, List

import langid  # type: ignore[import]
import pandas as pd
from rarc_utils.misc import plural
from yapic import json  # type: ignore[import]

from .core.types import (CaptionRec, ChannelId, ChannelRec, TableTypes,
                         VideoId, VideoRec)
from .db.helpers import compress_caption, create_many_items
from .db.models import Caption, Channel, Video, queryResult
from .settings import YOUTUBE_CHANNEL_PREFIX, YOUTUBE_VIDEO_PREFIX

logger = logging.getLogger(__name__)

LANGUAGE_CL = "language_cl"
LANGUAGE_CODE = "language_code"


class data_methods:
    """Data methods: methods for working with dataframes."""

    @staticmethod
    def extract_video_id(df: pd.DataFrame, urlCol="video_url") -> pd.DataFrame:
        """Extract YouTube's video_id from plain URL.

        example:
            https://www.youtube.com/watch?v=t0OX4jbFwvM --> t0OX4jbFwvM
        """
        assert urlCol in df.columns
        df = df.copy()
        df["video_id"] = df[urlCol].str.rsplit("?v=", n=1).str[1]

        return df

    @staticmethod
    def extract_channel_id(df: pd.DataFrame, urlCol="channel_url") -> pd.DataFrame:
        """Extract YouTube's channel_id from plain URL.

        example:
            https://www.youtube.com/channel/UC6ObzOWveHCMF --> UC6ObzOWveHCMF
        """
        assert urlCol in df.columns
        df = df.copy()
        df["channel_id"] = df[urlCol].str.rsplit("/channel/", n=1).str[1]

        return df

    @staticmethod
    def classify_language(df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Classify the language of a pandas str column."""
        assert column in df.columns, f"{column=} not in {df.columns=}"

        df = df.copy()

        df[LANGUAGE_CL] = df[column].map(langid.classify)
        df[LANGUAGE_CODE] = df[LANGUAGE_CL].map(itemgetter(0))
        df[LANGUAGE_CL] = df[LANGUAGE_CL].map(json.dumps)  # makes it serializable

        return df

    @staticmethod
    def keep_language(df: pd.DataFrame, lang_code: str) -> pd.DataFrame:
        """Keep only rows of language `lang_code`.

        caution: `classify_language` should run before this method
        """
        assert LANGUAGE_CL in df.columns
        assert LANGUAGE_CODE in df.columns

        lang_codes = df[LANGUAGE_CODE].to_list()
        if lang_code not in lang_codes:
            logger.error(f"no {lang_code=} rows in this dataset. {lang_codes=}")
            return pd.DataFrame()

        rows_before = len(df)
        df = df[df.language_code == lang_code].reset_index(drop=True)
        rows_after = len(df)

        logger.info(
            f"keeping {rows_after:,} rows. dismissed {rows_before - rows_after} non-{lang_code} rows"
        )

        return df

    @staticmethod
    def merge_captions_with_videos(
        df_captions: pd.DataFrame,
        df_videos: pd.DataFrame,
        dropCols=("language_cl", "language_code", "video_url"),
    ) -> pd.DataFrame:
        """Merge video and captions dataset on `video_id` column."""
        vdf = df_videos.drop(list(dropCols), axis=1)

        bdf = pd.merge(df_captions, vdf, left_on="video_id", right_on="video_id")

        logger.info("merged df_captions with df_videos")

        return bdf

    @staticmethod
    def create_df_from_cache(recs: List[dict]) -> pd.DataFrame:
        """Create DataFrame from PostgreSQL cache."""
        df = pd.DataFrame(recs)

        # reconstruct URL columns
        df["video_url"] = YOUTUBE_VIDEO_PREFIX + df["video_id"]
        df["channel_url"] = YOUTUBE_CHANNEL_PREFIX + df["channel_id"]
        df["qr_id"] = df["qr_id"].map(str)

        return df

    @classmethod
    async def push_videos(
        cls, vdf: pd.DataFrame, async_session
    ) -> Dict[str, Dict[str, TableTypes]]:
        """Push videos to db.

        First create Channel items
        """
        channel_recs = cls._make_channel_recs(vdf)

        records_dict = {}
        # create channels from same dataset
        records_dict["channel"] = await create_many_items(
            async_session, Channel, channel_recs, nameAttr="id", returnExisting=True
        )

        # map the new channels into vdf
        vdf["channel"] = vdf["channel_id"].map(records_dict["channel"])

        video_recs = cls._make_video_recs(vdf)

        records_dict["video"] = await create_many_items(
            async_session, Video, video_recs, nameAttr="id", returnExisting=True
        )

        logger.info("finished")

        return records_dict

    @classmethod
    async def push_captions(
        cls, df: pd.DataFrame, vdf: pd.DataFrame, async_session, returnExisting=True
    ) -> Dict[VideoId, Caption]:
        """Push captions to db.

        First create Channel and Video items

        returnExisting:     return captions after creating them
        """
        records_dict = await cls.push_videos(vdf, async_session)

        video_records = records_dict["video"]

        # save captions to postgres, or what other database: Redis, CassandraDB, DynamoDB?

        # map the videos into captions df
        df["video"] = df["video_id"].map(video_records)

        # compress captions
        df["compr"] = df["text"].map(compress_caption)
        df["compr_length"] = df["compr"].map(len)

        caption_recs = cls._make_caption_recs(df)

        captions = await create_many_items(
            async_session,
            Caption,
            caption_recs,
            nameAttr="video_id",
            returnExisting=returnExisting,
        )

        logger.info("finished")

        return captions

    @classmethod
    def push_query_results(
        cls,
        queryDict: Dict[str, Dict[str, TableTypes]],
        session,
    ) -> None:
        """Push queryResults to db."""
        if len(queryDict) == 0:
            return

        npushed: int = 0

        # qrs = [
        #     queryResult(query=query, videos=list(video_records.values()))
        #     for query, video_records in queryDict.items()
        # ]
        # session.add_all(qrs)

        for query, video_records in queryDict.items():
            videos: List[VideoRec] = list(video_records.values())

            qr = queryResult(query=query, videos=videos)
            print(f"{qr=}")
            session.add(qr)

            try:
                session.commit()
                npushed += 1
            except Exception as e:
                logger.warning(
                    f"could not create queryResults: \
                    \n\n{qr=} \nqr.dict={qr.as_dict()} \n\n{e=!r} \
                    \ntraceback: \n"
                )
                print(traceback.format_exc())

        # session.close()  # does not closing prevent triggers from triggering?

        query_results = plural(npushed, 'queryResult')
        logger.info(f"pushed {npushed} {query_results} to db")

    # ======================================================================= #
    # ======                       PRIVATE METHODS                     ====== #
    # ======================================================================= #

    @staticmethod
    def _make_channel_recs(df: pd.DataFrame) -> Dict[ChannelId, ChannelRec]:
        """Make Channel records from dataframe, for SQLAlchemy object creation."""
        recs = (
            df.rename(
                columns={
                    "channel_id": "id",
                    "channel_name": "name",
                }
            )[["id", "name", "num_subscribers"]]
            .assign(index=df["channel_id"])
            .set_index("index")
            .drop_duplicates()
            .to_dict("index")
        )

        return recs

    @staticmethod
    def _make_video_recs(df: pd.DataFrame) -> Dict[VideoId, VideoRec]:
        """Make Video records from dataframe, for SQLAlchemy object creation."""
        recs = (
            df.rename(columns={"video_id": "id",})[
                [
                    "id",
                    "title",
                    "description",
                    "views",
                    "custom_score",
                    "channel_id",
                    "channel",
                ]
            ]
            .assign(index=df["video_id"])
            .set_index("index")
            .drop_duplicates()
            .to_dict("index")
        )

        return recs

    @staticmethod
    def _make_caption_recs(df: pd.DataFrame) -> Dict[VideoId, CaptionRec]:
        """Make Caption records from dataframe, for SQLAlchemy object creation."""
        recs = (
            df.rename(
                columns={
                    "text_len": "length",
                    "language_code": "lang",
                }
            )[["video_id", "video", "length", "compr", "compr_length", "lang"]]
            .assign(index=df["video_id"])
            .set_index("index")
            .drop_duplicates()
            .to_dict("index")
        )

        return recs

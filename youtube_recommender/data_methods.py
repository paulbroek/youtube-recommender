"""data_methods.py, contains methods for working with dataframes."""

import logging
import traceback
import uuid
from collections import defaultdict
from operator import itemgetter
from typing import Dict, List

import langid  # type: ignore[import]
import pandas as pd
from rarc_utils.misc import map_list, plural
from yapic import json  # type: ignore[import]

from .core.types import (CaptionRec, ChannelId, ChannelRec, ChapterRec,
                         CommentId, CommentRec, TableTypes, VideoId, VideoRec)
from .db.helpers import (chapter_locations_to_df, compress_caption,
                         create_many_items, find_chapter_locations)
from .db.models import (Caption, Channel, Chapter, Comment, Keyword, Video,
                        queryResult)
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
    def extract_chapters(cls, vdf: pd.DataFrame) -> pd.DataFrame:
        """Extract Chapter metadata from Video.description."""
        logger.info(f"extracting chapters from video description")
        chapter_res: List[dict] = find_chapter_locations(
            vdf[["video_id", "length", "title", "description"]]
            .rename(columns={"video_id": "id"})
            .to_dict("records")
        )
        cdf = chapter_locations_to_df(chapter_res)

        vdf["chapters"] = vdf["video_id"].map(lambda x: [])

        if not cdf.empty:
            cdf = cls._make_chapter_df(cdf)

            by_vid = cdf[["video_id", "chapter"]].copy().groupby("video_id")
            chapters = by_vid["chapter"].apply(list).to_dict()

            # insert chapter lists into vdf
            # deal videos that do not have chapter information in description
            dd: defaultdict = defaultdict(list)
            dd.update(chapters)

            vdf["chapters"] = vdf["video_id"].map(dd)

        vdf["nchapter"] = vdf["chapters"].map(len)

        logger.info(f"chapters found: {vdf['nchapter'].sum():,}")

        return vdf

    @classmethod
    async def push_videos(
        cls, vdf: pd.DataFrame, async_session
    ) -> Dict[str, Dict[str, TableTypes]]:
        """Push videos to db.

        First create Keyword, Chapter and Channel items
        """
        vdf = vdf.copy()

        records_dict = {}

        keyword_recs = cls._make_keyword_recs(vdf)
        # todo: turn into transaction, since failing to create Video should remove the Keywords
        records_dict["keyword"] = await create_many_items(
            async_session, Keyword, keyword_recs, nameAttr="name", returnExisting=True
        )
        # map the keyword objects into vdf
        if "keywords" not in vdf.columns:
            vdf["keywords"] = vdf.apply(
                lambda x: [], axis=1
            )  # set to empty lists first
        else:
            vdf["keywords"] = vdf["keywords"].map(
                lambda x: map_list(x, records_dict["keyword"])
            )
            # and make them unique
            vdf["keywords"] = vdf["keywords"].map(set).map(list)

        channel_recs = cls._make_channel_recs(vdf)
        records_dict["channel"] = await create_many_items(
            async_session, Channel, channel_recs, nameAttr="id", returnExisting=True
        )

        # map the new channels into vdf
        vdf["channel"] = vdf["channel_id"].map(records_dict["channel"])

        video_recs = cls._make_video_recs(vdf)

        # remove existing video_ids from dataset, before pushing?
        # existing_video_ids = get_video_ids_by_ids(async_session, vdf.video_id.to_list())
        # drop those ids from dataframe

        records_dict["video"] = await create_many_items(
            async_session, Video, video_recs, nameAttr="id", returnExisting=True
        )

        logger.info("finished")

        return records_dict

    @classmethod
    async def push_comments(
        cls, df: pd.DataFrame, async_session, autobulk=True
    ) -> Dict[str, Dict[str, TableTypes]]:
        """Push comments to db.

        Assumes comments come from get_comments.py
        First map channels to dataset,
        get video_id, and update comments by video
        """
        df = df.copy()
        records_dict = {}

        # get/create channels
        df = df.rename(columns={"author": "channel_name", "channel": "channel_id"})
        channel_recs = cls._make_channel_recs(df, columns=("id", "name"))
        records_dict["channel"] = await create_many_items(
            async_session, Channel, channel_recs, nameAttr="id", returnExisting=True, autobulk=autobulk
        )
        # map the new channels into vdf
        df["channel"] = df["channel_id"].map(records_dict["channel"])

        # video_ids = df.video_id.unique()

        # get videos
        # videos = await get_videos_by_ids(async_session, video_ids)
        # records_dict["video"] = {v.id: v for v in videos}
        # print(f"{videos[0]=}")

        # # map videos into vdf
        # df["video"] = df["video_id"].map(records_dict["video"])

        comment_recs = cls._make_comment_recs(df, by_video_id=False)
        # comment_recs = cls._make_comment_recs(df, by_video_id=True)
        # print(f"{list(comment_recs.values())[0]=}")

        # best way? update comments per video?
        # does not work. maybe first create comments individually?

        records_dict["comment"] = await create_many_items(
            async_session, Comment, comment_recs, nameAttr="id", returnExisting=True, autobulk=autobulk
        )

        # todo: fix the case where video author is same as comment author. attached to different instance. 

        # async with async_session() as session:
        #     for video in videos:
        #         video.comments = comment_recs[video.id]

        #         await session.commit()

        #     print(f"{videos[0]=}")

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
        df, vdf = df.copy(), vdf.copy()
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

            qr = queryResult(
                id=uuid.uuid4(), query=query, videos=videos
            )  # id=uuid.uuid4(),
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

        query_results = plural(npushed, "queryResult")
        logger.info(f"pushed {npushed} {query_results} to db")

    # ======================================================================= #
    # ======                       PRIVATE METHODS                     ====== #
    # ======================================================================= #

    @staticmethod
    def _make_keyword_recs(df: pd.DataFrame) -> Dict[str, dict]:
        """Make Keyword records from dataframe, for SQLAlchemy object creation."""
        if "keywords" not in df.columns:
            return {}

        l: List[List[str]] = df.keywords.to_list()
        ll: List[str] = sum(l, [])
        ll = list(set(ll))

        recs = {k: {"name": k} for k in ll}

        return recs

    @staticmethod
    def _make_channel_recs(
        df: pd.DataFrame, columns=("id", "name", "num_subscribers")
    ) -> Dict[ChannelId, ChannelRec]:
        """Make Channel records from dataframe, for SQLAlchemy object creation."""
        recs = (
            df.rename(
                columns={
                    "channel_id": "id",
                    "channel_name": "name",
                }
            )[list(columns)]
            .assign(index=df["channel_id"])
            .set_index("index")
            .drop_duplicates("id")
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
                    "length",
                    "publish_date",
                    "custom_score",
                    "channel_id",
                    "channel",
                    "keywords",
                    "chapters",
                ]
            ]
            .assign(index=df["video_id"])
            .set_index("index")
            .drop_duplicates(subset="id")
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

    @staticmethod
    def _make_chapter_df(df: pd.DataFrame) -> pd.DataFrame:
        cdf = df.rename(columns={"s": "raw_str", "id": "video_id"})[
            [
                "video_id",
                "sub_id",
                "name",
                "raw_str",
                "start",
                "end",
            ]
        ].copy()

        cdf["chapter"] = cdf.drop("video_id", axis=1).apply(
            lambda x: Chapter(**x), axis=1
        )

        return cdf

    @staticmethod
    def _make_chapter_recs(df: pd.DataFrame) -> Dict[VideoId, ChapterRec]:
        """Make Chapter records from dataframe, for SQLAlchemy object creation."""
        recs = (
            df.rename(columns={"s": "raw_str"})[
                [
                    "sub_id",
                    "name",
                    "video_id",
                    "raw_str",
                    "start",
                    "end",
                ]
            ]
            .assign(
                index=pd.MultiIndex.from_frame(df[["video_id", "sub_id"]])
            )  # use both video_id and sub_id as index
            .set_index("index")
            .drop_duplicates()
            .to_dict("index")
        )

        return recs

    @staticmethod
    def _make_comment_recs(
        df: pd.DataFrame, by_video_id=True
    ) -> Dict[CommentId, CommentRec]:
        """Make Comment records from dataframe."""
        recs = (
            df.rename(columns={"cid": "id"})[
                [
                    "id",
                    "text",
                    "text",
                    "channel",
                    "channel_id",
                    "votes",
                    "time_parsed",
                    "video_id",
                ]
            ]
            .set_index("id", drop=False)
            .drop_duplicates()
            .to_dict("index")
        )

        if by_video_id:
            tdf = df.copy()
            tdf["rec"] = tdf["cid"].map(recs)
            tdf["comment"] = tdf["rec"].map(lambda x: Comment(**x))
            exp = tdf.groupby("video_id")["comment"].apply(list)

            recs_by_vid = exp.to_dict()

            return recs_by_vid

        return recs

r"""Youtube-recommender SQLAlchemy models.

creating a data model for any type of messages / tasks, ordering them by priority, sending reminders to a variety of sources, ...

based on:
    https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html

create database 'youtube' in psql (command line tool for postgres):
    (go inside psql) docker exec -it trade-postgres bash -c 'psql -U postgres -W'   ENTER PASSWORD, see file: trade/docker-compose-trade.yml

    CREATE DATABASE "youtube";

now connect using:
    docker exec -it trade-postgres bash -c 'psql youtube -U postgres'

create some tables using (from ./rarc/rarc directory):
    ipy -m youtube_recommender.db.models -- --create 0
    ipy -m youtube_recommender.db.models -- --create 1 -f  (create without asking for confirmation to delete existing models, use with caution)

list data:
    ipython --no-confirm-exit ~/repos/youtube/youtube/models.py -i -- --create 0

For migrations use alembic. First install `pip install psycopg2-binary` and `pip install alembic` in current conda environment. Run `alembic init alembic`  in this folder, 
and update "alembic.ini" by changing sqlalchemy.url to `postgresql://postgres:PASSWORD@77.249.149.174/youtube`
    - update the env.py file by importing your model:
        from models import *
        from models import Base
        target_metadata = Base.metadata

    - Change something in the model below, and run
        alembic revision --autogenerate -m "Add sum_amount column for Position"    for example
        Check the contents of the new alembic/versions/****Add_sum... file and if it correct run:

    - `alembic upgrade head` to commit all changes

    - Excellent documentations on: https://alembic.sqlalchemy.org/en/latest/autogenerate.html

Frequently used queries:

    see views.sql
    execute inside psql:
    docker exec -it postgres-master bash -c 'psql youtube -U postgres -f /youtube_data/db/views.sql'

Add trigger functions, so most frequently used views are always up to date:

    see triggers.sql
    execute inside psql:
    docker exec -it postgres-master bash -c 'psql youtube -U postgres -f /youtube_data/db/triggers.sql'


Get last videos:
    see queries.sql

    or query materialized view vw_last_videos:
        select * from vw_last_videos limit 5;

Refresh and show any materialized view:
    REFRESH MATERIALIZED VIEW last_messages;
    SELECT * FROM last_messages;

Show materialized views using:
        \dm
"""
import argparse
import asyncio
import logging
import uuid
from datetime import datetime, time

import timeago  # type: ignore[import]
from rarc_utils.log import loggingLevelNames, set_log_level, setup_logger
from rarc_utils.misc import trunc_msg
from rarc_utils.sqlalchemy_base import (UtilityBase, async_main, get_async_db,
                                        get_async_session, get_session,
                                        load_config)
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        Interval, LargeBinary, String, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Table
from youtube_recommender import config as config_dir

LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # title

Base = declarative_base()


psql = load_config(db_name="youtube", cfg_file="postgres.cfg", config_dir=config_dir)
psession = get_session(psql)()

# a video can have multiple keywords, a keyword can belong to multiple videos
video_keyword_association = Table(
    "video_keyword_association",
    Base.metadata,
    Column("video_id", String, ForeignKey("video.id")),
    Column("keyword_id", Integer, ForeignKey("keyword.id")),
    UniqueConstraint("video_id", "keyword_id"),
)

# a query_result can have multiple videos, a video can belong to multiple query results
query_video_association = Table(
    "query_video_association",
    Base.metadata,
    Column("query_result_id", UUID(as_uuid=True), ForeignKey("query_result.id")),
    Column("video_id", String, ForeignKey("video.id")),
    UniqueConstraint("query_result_id", "video_id"),
)


class VideoCategory(Base, UtilityBase):
    """VideoCategory: custom video categories for ease of filtering."""

    __tablename__ = "video_category"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=False)

    created = Column(DateTime, server_default=func.now())  # current_timestamp()

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "VideoCategory(name={})".format(self.name)

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Video(Base, UtilityBase):
    """Video: contains metadata of YouTube videos: views, title, id, etc."""

    __tablename__ = "video"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, unique=False)
    description = Column(String, nullable=True, unique=False)
    views = Column(Integer, nullable=False, unique=False)
    length = Column(Integer, nullable=False)
    publish_date = Column(DateTime)
    custom_score = Column(Float, nullable=True, unique=False)
    keywords = relationship(
        "Keyword", uselist=True, secondary=video_keyword_association, lazy="selectin"
    )
    comments = relationship(
        "Comment", uselist=True, back_populates="video", lazy="selectin"
    )
    is_educational = Column(Boolean)

    channel_id = Column(String, ForeignKey("channel.id"), nullable=False)
    channel = relationship("Channel", uselist=False, lazy="selectin")

    chapters = relationship("Chapter", uselist=True, lazy="selectin")
    # back_populates="video"

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Video(id={}, title={}, views={:,}, minutes={:.1f}, nkeyword={}, ncomment={}, is_educational={}, description={}, nchapter={})".format(
            self.id,
            trunc_msg(self.title, 40),
            self.views,
            self.length / 60,
            len(self.keywords),
            len(self.comments),
            self.is_educational,
            trunc_msg(self.description, 40),
            len(self.chapters),
        )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Chapter(Base, UtilityBase):
    """Chapter: relates to Video, contains a string that describes a part of the video, set by user."""

    __tablename__ = "chapter"
    # use a composite Id: videoId + sub_id, so that you can easily query by asdf923j3j-2, the second chatper of a video
    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column(String, primary_key=True)
    sub_id = Column(Integer, nullable=False, unique=False)

    # unique or not? are authors allowed to make mistakes in this?
    name = Column(String, nullable=False, unique=False)
    video_id = Column(String, ForeignKey("video.id"), nullable=False)
    video = relationship("Video", uselist=False, lazy="selectin")

    raw_str = Column(String, nullable=False)

    # together, start and end should be unique, sometimes author makes a mistakes and reuses the same start value
    # add unix index for this
    start = Column(Interval, nullable=False, unique=False)
    end = Column(Interval, nullable=False, unique=False)
    UniqueConstraint(
        "video_id", "sub_id", "start", "end", name="unique_start_end_chapter"
    )

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Chapter(id={}, video.title={}, sub_id={}, name={}, start={}, end={}, minute_length={:.1f})".format(
            trunc_msg(self.id.__str__(), 8),
            trunc_msg(self.video.title, 40) if self.video else "NaN",
            self.sub_id,
            self.name,
            self.start,
            self.end,
            # self.length(),
            0.00,
        )

    def length(self):
        return (self.end - self.start).total_seconds() / 60

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        d = self.as_dict()
        for key in ("start", "end"):
            d[key] = d[key].isoformat()

        for key in ("created", "updated"):
            d.pop(key, None)

        return d

    @staticmethod
    def from_json(jsonDict: dict):
        """Create model instance from json."""
        for key in ("start", "end"):
            jsonDict[key] = time.fromisoformat(jsonDict[key])
        for key in ("created", "updated"):
            if key in jsonDict:
                jsonDict[key] = datetime.fromisoformat(jsonDict[key])

        return Chapter(**jsonDict)


class Channel(Base, UtilityBase):
    """Channel: contains compressed captions in Bytes for YouTube videos.

    channels also represent users.
    """

    __tablename__ = "channel"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=False)
    num_subscribers = Column(
        Integer, nullable=True, unique=False
    )  # nullable=False for now, since pytube does not collect this information, can request later through youtube API v3 (single calls)
    nvideo = Column(Integer, nullable=True, unique=False)
    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_scrape = Column(DateTime)

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Channel(id={}, name={}, nvideo={}, num_subscribers={}, last_scrape={})".format(
            self.id,
            self.name,
            self.nvideo,
            self.num_subscribers,
            self.last_scrape_ago(),
        )

    def last_scrape_ago(self) -> str:
        res: str = ""
        if self.last_scrape is not None:
            res = timeago.format(self.last_scrape, datetime.utcnow())

        return res

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Comment(Base, UtilityBase):
    """Comment: YouTube comments."""

    __tablename__ = "comment"
    id = Column(String, primary_key=True)
    text = Column(String, nullable=False, unique=False)
    votes = Column(Integer, nullable=False)

    # channel also represents a user
    channel_id = Column(String, ForeignKey("channel.id"), nullable=False)
    channel = relationship("Channel", uselist=False, lazy="selectin")

    video_id = Column(String, ForeignKey("video.id"), nullable=False)
    video = relationship("Video", uselist=False, lazy="selectin")

    time_parsed = Column(DateTime)
    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return (
            "Comment(id={}, text={}, votes={:,}, channel_name={}, video_id={})".format(
                self.id,
                trunc_msg(self.text, 40),
                self.votes,
                self.channel.name,
                self.video_id,
            )
        )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Keyword(Base, UtilityBase):
    """Keyword: every Video can contain keywords, set by the author."""

    __tablename__ = "keyword"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    created = Column(DateTime, server_default=func.now())  # current_timestamp()

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Keyword(id={}, name={})".format(self.id, self.name)

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Caption(Base, UtilityBase):
    """Caption: contains compressed captions in Bytes for YouTube videos."""

    __tablename__ = "caption"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    video_id = Column(String, ForeignKey("video.id"), nullable=False)
    video = relationship("Video", uselist=False, lazy="selectin")

    length = Column(Integer, nullable=False)
    compr = Column(LargeBinary, nullable=False)
    compr_length = Column(Integer, nullable=False)
    lang = Column(String, nullable=False)

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Caption(id={}, video.title={}, length={:_}, compr_length={:_}, compr%={:.2%})".format(
            trunc_msg(self.id.__str__(), 8),
            trunc_msg(self.video.title, 40),
            self.length,
            self.compr_length,
            self.compr_pct(),
        )

    def compr_pct(self) -> float:
        return self.compr_length / self.length

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class scrapeJob(Base, UtilityBase):
    """scrapeJob: a scrapeJob is related to a Channel. Since channels can upload new videos,
    this table shows user when it was scraped for the last time, and how many videos.

    """

    __tablename__ = "scrape_job"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        nullable=False,
        default=uuid.uuid4,
    )

    channel_id = Column(String, ForeignKey("channel.id"), nullable=False)
    channel = relationship("Channel", uselist=False, lazy="selectin")

    nupdate = Column(Integer, default=0)
    done = Column(Boolean)

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return (
            "scrapeJob(id={}, channel={}, nupdate={}, done={}, updated_ago={})".format(
                str(self.id),
                self.channel.name,
                self.nupdate,
                self.done,
                timeago.format(self.updated, datetime.utcnow())
                if self.updated
                else None,
            )
        )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class queryResult(Base, UtilityBase):
    """queryResult: YouTube API search query, used to cache search results.

    To not overrequest their API
    """

    __tablename__ = "query_result"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        nullable=False,
        default=uuid.uuid4,
    )

    # todo: save the entire query, also `publishedAfter` and `relevanceLanguage`
    # make sure to lower the string before entering
    query = Column(String, nullable=False, unique=False)
    # not unique, but will only add new query_results after N days have elapsed
    # nresult = Column(Integer, nullable=False, unique=False)

    videos = relationship(
        "Video", uselist=True, secondary=query_video_association, lazy="selectin"
    )
    # lazy=True

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "queryResult(id={}, query={}, nresult={}, updated_ago={})".format(
            str(self.id),
            self.query,
            len(self.videos),
            timeago.format(self.updated, datetime.utcnow()) if self.updated else None,
        )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


# def find_chapters_for_existing_videos(n=1_000) -> pd.DataFrame:

#     q = select(Video).limit(5000)
#     res = psession.execute(q).scalars().fetchall()
#     ret = find_chapter_locations([r.as_dict() for r in res])
#     df = chapter_locations_to_df(ret)

#     return df


if __name__ == "__main__":

    CLI = argparse.ArgumentParser()
    CLI.add_argument(
        "-v",
        "--verbosity",
        type=str,
        default="info",
        help=f"choose debug log level: {', '.join(loggingLevelNames())}",
    )
    CLI.add_argument(
        "--create",
        type=int,
        default=0,
        help="create new models (1), or use existing ones (0)",
    )
    CLI.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="don't ask for model creation confirmation. \
            caution: deletes all existing models",
    )

    args = CLI.parse_args()

    async_session = get_async_session(psql)
    async_db = get_async_db(psql)()

    loop = asyncio.new_event_loop()

    log_level = args.verbosity.upper()
    logger = setup_logger(
        cmdLevel=logging.DEBUG, saveFile=0, savePandas=0, color=1, fmt=LOG_FMT
    )
    set_log_level(logger, level=log_level, fmt=LOG_FMT)

    if args.create:
        print("create models")
        loop.run_until_complete(
            async_main(psql, base=Base, force=args.force, dropFirst=True)
        )

        # print('create data')
        # items = loop.run_until_complete(create_initial_items(async_session))
        # loop.run_until_complete(create_initial_items(async_session))
    else:
        print("get data")
        # data = loop.run_until_complete(get_data2(psql))

    # strMappings = loop.run_until_complete(aget_str_mappings(psql))

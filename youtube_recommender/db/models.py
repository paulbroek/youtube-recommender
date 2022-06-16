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
and update "alembic.ini" by changing sqlalchemy.url to `postgresql://postgres:PASSWORD@80.56.112.182/youtube`
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
import configparser
import logging
import uuid
from datetime import datetime
from pathlib import Path

import timeago  # type: ignore[import]
from rarc_utils.log import loggingLevelNames, set_log_level, setup_logger
from rarc_utils.misc import AttrDict, trunc_msg
from rarc_utils.sqlalchemy_base import (UtilityBase, async_main, get_async_db,
                                        get_async_session, get_session)
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer,
                        LargeBinary, String, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Table
from youtube_recommender import config as config_dir

# __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # title
# logger = logging.getLogger(__name__)
# print(f"{__location__=}")

# ugly way of retrieving postgres cfg file
p = Path(config_dir.__file__)
# p = Path(__location__)
# p = p / "db"
cfgFile = p.with_name("postgres.cfg")

parser = configparser.ConfigParser()
parser.read(cfgFile)
psql = AttrDict(parser["psql"])
assert psql["db"] == "youtube"  # do not overwrite existing other db
psession = get_session(psql)()

DATA_DIR = Path("data")

Base = declarative_base()

# a query_result can have multiple videos, a video can belong to multiple query results
query_video_association = Table(
    "query_video_association",
    Base.metadata,
    Column("query_result_id", UUID(as_uuid=True), ForeignKey("query_result.id")),
    Column("video_id", String, ForeignKey("video.id")),
    UniqueConstraint("query_result_id", "video_id"),
)


class Video(Base, UtilityBase):
    """Video: contains metadata of YouTube videos: views, title, id, etc."""

    __tablename__ = "video"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, unique=False)
    description = Column(String, nullable=True, unique=False)
    views = Column(Integer, nullable=False, unique=False)
    custom_score = Column(Float, nullable=True, unique=False)

    channel_id = Column(String, ForeignKey("channel.id"), nullable=False)
    channel = relationship("Channel", uselist=False, lazy="selectin")

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Video(id={}, title={}, views={:,}, description={})".format(
            self.id,
            trunc_msg(self.title, 40),
            self.views,
            trunc_msg(self.description, 40),
        )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def json(self) -> dict:
        return self.as_dict()


class Channel(Base, UtilityBase):
    """Channel: contains metadata of YouTube channels: num_subscribers, id, etc."""

    __tablename__ = "channel"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=False)
    num_subscribers = Column(Integer, nullable=False, unique=False)

    created = Column(DateTime, server_default=func.now())  # current_timestamp()
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # add this so that it can be accessed
    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self):
        return "Channel(id={}, name={}, num_subscribers={})".format(
            self.id, self.name, self.num_subscribers
        )

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


class queryResult(Base, UtilityBase):
    """queryResult: YouTube API search query, used to cache search results.

    To not overrequest their API
    """

    __tablename__ = "query_result"
    id = Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False, default=uuid.uuid4)

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


if __name__ == "__main__":

    CLI = argparse.ArgumentParser()
    CLI.add_argument(
        "-v",
        "--verbosity",
        type=str,
        default="info",
        help=f"choose debug log level: {', '.join(loggingLevelNames())} ",
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
        # raise NotImplementedError

    # strMappings = loop.run_until_complete(aget_str_mappings(psql))

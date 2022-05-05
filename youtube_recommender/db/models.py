"""
    enabler SQLAlchemy models
    creating a data model for any type of messages / tasks, ordering them by priority, sending reminders to a variety of sources, ...

    based on:
         https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html 

    create database 'enabler' in psql (command line tool for postgres):
        (go inside psql) docker exec -it trade-postgres bash -c 'psql -U postgres -W'   ENTER PASSWORD, see file: trade/docker-compose-trade.yml
        
        CREATE DATABASE "enabler";

    now connect using:
        docker exec -it trade-postgres bash -c 'psql enabler -U postgres'

    create some tables using (from ./rarc/rarc directory):
        ipython --no-confirm-exit ~/repos/youtube-recommender/youtube-recommender/db/models.py -i -- --create 1
        ipython --no-confirm-exit ~/repos/youtube-recommender/youtube-recommender/db/models.py -i -- --create 1 -f  (create without asking for confirmation to delete existing models, use with caution)

    list data:
        ipython --no-confirm-exit ~/repos/enabler/enabler/models.py -i -- --create 0

    For migrations use alembic. First install `pip install psycopg2-binary` and `pip install alembic` in current conda environment. Run `alembic init alembic`  in this folder, 
    and update "alembic.ini" by changing sqlalchemy.url to `postgresql://postgres:PASSWORD@80.56.112.182/enabler`
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
        docker exec -it postgres-master bash -c 'psql enabler -U postgres -f /enabler_data/db/views.sql'

   Add trigger functions, so most frequently used views are always up to date:

        see triggers.sql
        execute inside psql:
        docker exec -it postgres-master bash -c 'psql enabler -U postgres -f /enabler_data/db/triggers.sql'

    Get last messages:

        (show view content)
        SELECT * FROM last_messages;

    Get tasks by user:

        REFRESH MATERIALIZED VIEW last_tasks;
        SELECT *, NOW() - task.updated AS updated_ago, task.due_date - NOW() AS till_due
        FROM last_tasks AS task
        WHERE user_id = 2;

    Refresh and show any materialized view:
        REFRESH MATERIALIZED VIEW last_messages;
        SELECT * FROM last_messages;

    Show materialized views using: 
        \dm

"""

import os
import argparse

# from datetime import timedelta, datetime

# from collections import defaultdict
import configparser
import asyncio
import logging

# from random import sample, choice
from pathlib import Path

# import uuid
# import json

# from pprint import pprint
# from yapic import json

# from sqlalchemy import and_
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    func,
    Integer,
    BigInteger,
    String,
    Interval,
    Boolean,
    Float,
)  # , Index, PickleType
from sqlalchemy import UniqueConstraint, CheckConstraint  # ,  ForeignKeyConstraint

# from sqlalchemy.dialects.postgresql import JSON #, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

# from sqlalchemy.orm import selectinload

# import pandas as pd

# import numpy as np

# from lorem_text import lorem

from rarc_utils.sqlalchemy_base import (
    async_main,
    get_session,
    get_async_session,
    get_async_db,
    aget_or_create,
    UtilityBase,
)  # , run_in_session, get_or_create, AbstractBase,
from rarc_utils.log import setup_logger, set_log_level, loggingLevelNames
from rarc_utils.misc import AttrDict, trunc_msg  # , timeago_series

# import rarc_utils.config.redis as redis_config
# from enabler import config as config_dir
from .helpers import *

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

LOG_FMT = "%(asctime)s - %(module)-16s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # title
logger = logging.getLogger(__name__)
print(f"{__location__=}")

# ugly way of retrieving postgres cfg file
# p = Path(config_dir.__file__)
p = Path(__location__)
p = p / "db"
cfgFile = p.with_name("postgres.cfg")

parser = configparser.ConfigParser()
parser.read(cfgFile)
psql = AttrDict(parser["psql"])
assert psql["db"] == "youtube"  # just to be save to not overwrite existing other db
psession = get_session(psql)()

DATA_DIR = Path("data")

Base = declarative_base()


class Video(Base, UtilityBase):
    """Video: contains metadata of YouTube videos: views, title, id, etc"""

    __tablename__ = "video"
    id = Column(String, primary_key=True)
    # id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    """Chanenel: contains metadata of YouTube channels: num_subscribers, id, ..."""

    __tablename__ = "channel"
    # id              = Column(Integer, primary_key=True)
    id = Column(String, primary_key=True)
    # id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
        help="don't ask for model creation confirmation. caution: deletes all existing models",
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

    strMappings = loop.run_until_complete(aget_str_mappings(psql))

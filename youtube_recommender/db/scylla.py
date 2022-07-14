"""scylla.py.

ScyllaDB connector

For now, copied from: 
    https://python-driver.docs.scylladb.com/stable/object_mapper.html

Usage:

cd ~/repos/youtube-recommender
# create new models
ipy youtube_recommender/db/scylla.py -i -- --create 1
# only load models
ipy youtube_recommender/db/scylla.py -i -- --create 0
"""

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import List

import numpy as np
from cassandra.cqlengine import columns, connection  # type: ignore[import]
from cassandra.cqlengine.management import (  # type: ignore[import]
    create_keyspace_simple, sync_table)
from cassandra.cqlengine.models import Model  # type: ignore[import]
from cassandra.cqlengine.query import BatchQuery  # type: ignore[import]
from dotenv import load_dotenv
from rarc_utils.decorators import items_per_sec
from tqdm import tqdm  # type: ignore[import]

load_dotenv()
logger = logging.getLogger(__name__)

SCYLLA_KEYSPACE = os.environ.get("SCYLLA_KEYSPACE")
SCYLLA_HOST = os.environ.get("SCYLLA_HOST")
connection.setup([SCYLLA_HOST], SCYLLA_KEYSPACE, protocol_version=3)


class ExampleModel(Model):
    __key_space__ = SCYLLA_KEYSPACE

    example_id = columns.UUID(primary_key=True, default=uuid.uuid4)
    example_type = columns.Integer(index=True)
    created_at = columns.DateTime()
    description = columns.Text(required=False)


class Comment(Model):
    """Comment model that replicates db.models.Comment."""

    __key_space__ = SCYLLA_KEYSPACE

    id = columns.Text(primary_key=True)
    text = columns.Text(required=True)
    votes = columns.Integer(index=True)
    channel_id = columns.Text(index=True)
    video_id = columns.Text(index=True)
    time_parsed = columns.DateTime()
    created_at = columns.DateTime()


@items_per_sec
def push_comments_scylla(items: List[dict], batchsize=2_000, model=Comment):
    """Push comments in batch to ScyllaDB.

    Usage:
        from youtube_recommender.data_methods import data_methods as dm
        from youtube_recommender.db.scylla import push_comments_scylla
        df = df.rename(columns = {"cid": "id"})
        df["textlen"] = df.text.map(len)
        df = df[df.textlen > 0].copy()
        recs = dm._make_comment_recs_scylla(df)
        push_comments_scylla(list(recs.values()), batchsize=1_000)
    """
    b = BatchQuery()
    nbatch = int(len(items) / batchsize)

    logger.info(f"{nbatch=}")

    for batch in tqdm(np.array_split(items, nbatch)):
        with BatchQuery() as b:
            for item in batch:
                item["created_at"] = datetime.now()
                model.batch(b).create(**item)

@items_per_sec
def get_comments_scylla(n=None) -> List[dict]:
    """Get comments from ScyllaDB.

    Usage:
        from youtube_recommender.data_methods import data_methods as dm
        from youtube_recommender.db.scylla import push_comments_scylla
        df = df.rename(columns = {"cid": "id"})
        df["textlen"] = df.text.map(len)
        df = df[df.textlen > 0].copy()
        recs = dm._make_comment_recs_scylla(df)
        push_comments_scylla(list(recs.values()), batchsize=1_000)
    """
    query = Comment.objects()

    if n is not None:
        query = query.limit(n)

    return list([dict(o) for o in query])

parser = argparse.ArgumentParser(description="Define get_coments parameters")
parser.add_argument(
    "--create",
    type=int,
    default=0,
    help="create=1 -> create models",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # next, setup the connection to your cassandra server(s)...
    # see http://datastax.github.io/python-driver/api/cassandra/cluster.html for options
    # the list of hosts will be passed to create a Cluster() instance

    if not args.create:
        sys.exit()

    # create keyspace before creating any tables
    create_keyspace_simple(SCYLLA_KEYSPACE, 1)

    # create CQL tables
    sync_table(ExampleModel)
    sync_table(Comment)

    # create some rows
    em1 = ExampleModel.create(
        example_type=0, description="example1", created_at=datetime.now()
    )
    em2 = ExampleModel.create(
        example_type=0, description="example2", created_at=datetime.now()
    )
    em3 = ExampleModel.create(
        example_type=1, description="example3", created_at=datetime.now()
    )
    em4 = ExampleModel.create(
        example_type=1, description="example4", created_at=datetime.now()
    )

    # run some queries against our table
    ExampleModel.objects.count()
    q = ExampleModel.objects(example_type=1)
    q.count()
    for instance in q:
        print(instance.description)

    # here we are applying additional filtering to an existing query
    # query objects are immutable, so calling filter returns a new
    # query object
    q2 = q.filter(example_id=em3.example_id)

    q2.count()
    for instance in q2:
        print(instance.description)

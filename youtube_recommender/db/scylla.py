"""scylla.py.

ScyllaDB connector
"""

import os
import uuid
from datetime import datetime

from cassandra.cqlengine import columns, connection
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine.models import Model
from dotenv import load_dotenv

load_dotenv()


#first, define a model
class ExampleModel(Model):
    example_id      = columns.UUID(primary_key=True, default=uuid.uuid4)
    example_type    = columns.Integer(index=True)
    created_at      = columns.DateTime()
    description     = columns.Text(required=False)

#next, setup the connection to your cassandra server(s)...
# see http://datastax.github.io/python-driver/api/cassandra/cluster.html for options
# the list of hosts will be passed to create a Cluster() instance
SCYLLA_HOST = os.environ.get("SCYLLA_HOST")
connection.setup([SCYLLA_HOST], "cqlengine", protocol_version=3)

#...and create your CQL table
sync_table(ExampleModel)

#now we can create some rows:
em1 = ExampleModel.create(example_type=0, description="example1", created_at=datetime.now())
em2 = ExampleModel.create(example_type=0, description="example2", created_at=datetime.now())
em3 = ExampleModel.create(example_type=0, description="example3", created_at=datetime.now())
em4 = ExampleModel.create(example_type=0, description="example4", created_at=datetime.now())
em5 = ExampleModel.create(example_type=1, description="example5", created_at=datetime.now())
em6 = ExampleModel.create(example_type=1, description="example6", created_at=datetime.now())
em7 = ExampleModel.create(example_type=1, description="example7", created_at=datetime.now())
em8 = ExampleModel.create(example_type=1, description="example8", created_at=datetime.now())

#and now we can run some queries against our table
ExampleModel.objects.count()
q = ExampleModel.objects(example_type=1)
q.count()
for instance in q:
    print(instance.description)

#here we are applying additional filtering to an existing query
#query objects are immutable, so calling filter returns a new
#query object
q2 = q.filter(example_id=em5.example_id)

q2.count()
for instance in q2:
    print(instance.description)

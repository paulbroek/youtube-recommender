import os

import grpc
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import ChannelScrapingsStub

host = os.environ.get("YT_SCRAPE_SERVICE_HOST", None)
assert host is not None

channel = grpc.insecure_channel(f"{host}:50051")
client = ChannelScrapingsStub(channel)
request = ScrapeRequest(
    id=0,
    category=ScrapeCategory.CHANNEL,
    value="https://www.youtube.com/c/GotoConferences",
)
res = client.Scrape(request)
print(f"{res=}")

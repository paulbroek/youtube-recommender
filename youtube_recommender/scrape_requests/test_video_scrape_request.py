"""test_video_scrape_request.py

Run:
    export YT_SCRAPE_SERVICE_HOST=localhost         && ipy test_video_scrape_request.py
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_video_scrape_request.py
"""

import os

import grpc  # type: ignore[import]
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import VideoScrapingsStub

# host = "localhost"
# host = "192.168.178.46"
host = os.environ.get("YT_SCRAPE_SERVICE_HOST", None)
assert host is not None
channel = grpc.insecure_channel(f"{host}:50051")
client = VideoScrapingsStub(channel)
request = ScrapeRequest(
    id=0,
    category=ScrapeCategory.VIDEO,
    value="https://www.youtube.com/watch?v=GBTdnfD6s5Q",
)
res = client.Scrape(request)
print(f"{res=}")

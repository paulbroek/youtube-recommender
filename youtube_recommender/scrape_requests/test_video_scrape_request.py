"""test_video_scrape_request.py

Run:
    # run serve.py first
    # python serve.py, OR docker-compose build && docker-compose up -d scrape-service
    export YT_SCRAPE_SERVICE_HOST=localhost         && ipy test_video_scrape_request.py
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_video_scrape_request.py
"""

import os

import grpc  # type: ignore[import]
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import VideoScrapingsStub

host = os.environ.get("YT_SCRAPE_SERVICE_HOST", None)
port = os.environ.get("YT_SCRAPE_SERVICE_PORT", 50051)
assert host is not None
assert port is not None

channel = grpc.insecure_channel(f"{host}:{port}")
channel = grpc.insecure_channel(f"{host}:50051")
client = VideoScrapingsStub(channel)
request = ScrapeRequest(
    id=0,
    category=ScrapeCategory.VIDEO,
    value="https://www.youtube.com/watch?v=GBTdnfD6s5Q",
)
res = client.Scrape(request)
print(f"{res=}")

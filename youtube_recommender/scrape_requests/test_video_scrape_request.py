import grpc
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import VideoScrapingsStub

# host = "localhost"
host = "192.168.178.46"
channel = grpc.insecure_channel(f"{host}:50051")
client = VideoScrapingsStub(channel)
request = ScrapeRequest(
    id=0,
    category=ScrapeCategory.VIDEO,
    value="https://www.youtube.com/watch?v=GBTdnfD6s5Q",
)
res = client.Scrape(request)
print(f"{res=}")

import grpc
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import ChannelScrapingsStub

channel = grpc.insecure_channel("localhost:50051")
client = ChannelScrapingsStub(channel)
request = ScrapeRequest(
    id=0,
    category=ScrapeCategory.CHANNEL,
    value="https://www.youtube.com/c/GotoConferences",
)
res = client.Scrape(request)
print(f"{res=}")

# scrape_requests/scrape_requests.py
from concurrent import futures

import grpc  # type: ignore[import]
import pandas as pd
import scrape_requests_pb2_grpc
from pytube import Channel as pytube_channel  # type: ignore[import]
from scrape_requests_pb2 import (ChannelScrapeResponse, ChannelScrapeResult,
                                 ScrapeCategory)
from youtube_recommender.pytube_scrape import extract_channel_fields

cats = ScrapeCategory.values()


class ChannelScrapeService(scrape_requests_pb2_grpc.ChannelScrapingsServicer):
    def Scrape(self, request, context):
        if request.category not in ScrapeCategory.values():
            context.abort(grpc.StatusCode.NOT_FOUND, "Category not found")

        if request.value == "":
            context.abort(grpc.StatusCode.OUT_OF_RANGE, "value missing")

        print(f"{request.value=}")

        if request.category == ScrapeCategory.CHANNEL:
            # todo: your pytube scrape code for Channel, Video or Comment
            # or should success be omitted, and errors caught by Interceptors?
            vurls: pytube_channel = pytube_channel(request.value)

            fields = extract_channel_fields(request.value)
            fields["vurls"] = list(vurls)
            results = [ChannelScrapeResult(**fields)]

            # print(f"{dir(request)=}")
            # print(f"{request.category=}")
            # print(f"{type(request.category)=}")
            # category = random.choice(cats)
            category: int = request.category
            # category = 0
            # results = [
            #     ChannelScrapeResult(id=str(uuid.uuid1()), category=category, success=True)
            # ]

        else:
            raise NotImplementedError

        return ChannelScrapeResponse(channelScrapeResults=results)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    scrape_requests_pb2_grpc.add_ChannelScrapingsServicer_to_server(
        ChannelScrapeService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

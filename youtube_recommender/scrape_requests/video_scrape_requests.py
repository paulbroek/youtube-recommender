# scrape_requests/scrape_requests.py
import logging
from concurrent import futures

import grpc  # type: ignore[import]
import pandas as pd
import scrape_requests_pb2_grpc
from scrape_requests_pb2 import (ScrapeCategory, VideoScrapeResponse,
                                 VideoScrapeResult)
from youtube_recommender.pytube_scrape import extract_video_fields

cats = ScrapeCategory.values()

logger = logging.getLogger(__name__)


class VideoScrapeService(scrape_requests_pb2_grpc.VideoScrapingsServicer):
    def Scrape(self, request, context):
        if request.category not in ScrapeCategory.values():
            context.abort(grpc.StatusCode.NOT_FOUND, "Category not found")

        if request.value == "":
            context.abort(grpc.StatusCode.OUT_OF_RANGE, "value missing")

        logger.debug(f"{request.value=}")

        if request.category == ScrapeCategory.VIDEO:
            fields: dict = extract_video_fields(request.value, isodate=True)
            results = [VideoScrapeResult(**fields)]
            # results = [ScrapeResult(id=str(uuid.uuid1()), category=category, success=True)]

        else:
            raise NotImplementedError

        return VideoScrapeResponse(videoScrapeResults=results)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    scrape_requests_pb2_grpc.add_VideoScrapingsServicer_to_server(
        VideoScrapeService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

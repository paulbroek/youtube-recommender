# scrape_requests/scrape_requests.py
from concurrent import futures
from typing import Any, Dict, List

import grpc  # type: ignore[import]
import scrape_requests_pb2_grpc
from scrape_requests_pb2 import (CommentScrapeResponse, CommentScrapeResult,
                                 ScrapeCategory)
from youtube_recommender.get_comments import get_comments_list

cats = ScrapeCategory.values()

# todo: use logging or Interceptors?

class CommentScrapeService(scrape_requests_pb2_grpc.CommentScrapingsServicer):
    def Scrape(self, request, context):
        if request.category not in ScrapeCategory.values():
            context.abort(grpc.StatusCode.NOT_FOUND, "Category not found")

        if request.value == "":
            context.abort(grpc.StatusCode.OUT_OF_RANGE, "value missing")

        print("request: \n{}".format(request))

        if request.category == ScrapeCategory.COMMENT:
            comments: List[Dict[str, Any]] = get_comments_list(request.value)
            print(f"{len(comments):,} comments")
            results = [CommentScrapeResult(**comment) for comment in comments]

        else:
            raise NotImplementedError

        return CommentScrapeResponse(commentScrapeResults=results)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    scrape_requests_pb2_grpc.add_CommentScrapingsServicer_to_server(
        CommentScrapeService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

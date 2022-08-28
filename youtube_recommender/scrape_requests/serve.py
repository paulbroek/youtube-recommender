"""serve.py.

Run:
    python serve.py
    python serve.py --max_workers 20
"""
import argparse
from concurrent import futures

import grpc  # type: ignore[import]
import scrape_requests_pb2_grpc
from channel_scrape_requests import ChannelScrapeService
from comment_scrape_requests import CommentScrapeService
from video_scrape_requests import VideoScrapeService

# todo: fix with docker-secrets
# with open("/cert/nginx.crt", "rb") as f:
#     trusted_certs = f.read()


def serve(max_workers):
    # todo: does this workflow needs async functionality?
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    scrape_requests_pb2_grpc.add_ChannelScrapingsServicer_to_server(
        ChannelScrapeService(), server
    )
    scrape_requests_pb2_grpc.add_VideoScrapingsServicer_to_server(
        VideoScrapeService(), server
    )
    scrape_requests_pb2_grpc.add_CommentScrapingsServicer_to_server(
        CommentScrapeService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


parser = argparse.ArgumentParser(description="cli parameters")
parser.add_argument(
    "--max_workers",
    type=int,
    default=10,
    help="max_workers / threads",
)

if __name__ == "__main__":
    cli_args = parser.parse_args()
    serve(cli_args.max_workers)

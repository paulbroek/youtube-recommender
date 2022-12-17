"""serve.py.

Run:
    python serve.py
    python serve.py --max_workers 20
"""
import argparse
import logging
from concurrent import futures

import grpc  # type: ignore[import]
import scrape_requests_pb2_grpc
from channel_scrape_requests import ChannelScrapeService
from comment_scrape_requests import CommentScrapeService
from interceptors import ErrorLogger
from rarc_utils.log import LOG_FMT, setup_logger
from video_scrape_requests import VideoScrapeService

with open("/run/secrets/nginx.key", "rb") as f:  # path to you key location
    private_key = f.read()
with open("/run/secrets/nginx.cert", "rb") as f:
    certificate_chain = f.read()

server_credentials = grpc.ssl_server_credentials(
    (
        (
            private_key,
            certificate_chain,
        ),
    )
)


def serve(max_workers, secure=False):
    # todo: does this workflow need async functionality?
    # no, because mostly clients use async calls, always be carefull to use async functionality in server
    interceptors = [ErrorLogger()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers), interceptors=interceptors
    )
    scrape_requests_pb2_grpc.add_ChannelScrapingsServicer_to_server(
        ChannelScrapeService(), server
    )
    scrape_requests_pb2_grpc.add_VideoScrapingsServicer_to_server(
        VideoScrapeService(), server
    )
    scrape_requests_pb2_grpc.add_CommentScrapingsServicer_to_server(
        CommentScrapeService(), server
    )
    if secure:
        server.add_secure_port("[::]:50051", server_credentials)
    else:
        server.add_insecure_port("[::]:50051")

    server.start()
    server.wait_for_termination()


parser = argparse.ArgumentParser(description="cli parameters")
parser.add_argument(
    "--secure",
    action="store_true",
    help="secure gRPC channels with SSL",
)
parser.add_argument(
    "--max_workers",
    type=int,
    default=10,
    help="max_workers / threads",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="show debug output",
)

if __name__ == "__main__":
    cli_args = parser.parse_args()

    logger = setup_logger(
        cmdLevel=logging.DEBUG if cli_args.debug else logging.INFO,
        saveFile=0,
        savePandas=0,
        color=1,
        fmt=LOG_FMT,
    )
    # logger = logging.getLogger(__name__)
    logger.info("running")

    serve(cli_args.max_workers, secure=cli_args.secure)

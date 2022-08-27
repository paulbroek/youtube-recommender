from concurrent import futures

import grpc
import scrape_requests_pb2_grpc
from channel_scrape_requests import ChannelScrapeService
from video_scrape_requests import VideoScrapeService


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    scrape_requests_pb2_grpc.add_ChannelScrapingsServicer_to_server(
        ChannelScrapeService(), server
    )
    scrape_requests_pb2_grpc.add_VideoScrapingsServicer_to_server(
        VideoScrapeService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

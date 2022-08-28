r"""test_scrape_request.py

Run:
    # run serve.py first
    # python serve.py, OR docker-compose build && docker-compose up -d scrape-service
    export YT_SCRAPE_SERVICE_HOST=localhost         && ipy test_scrape_request.py -- --category video   --id GBTdnfD6s5Q --aio --ntrial 10
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_scrape_request.py -- --category video   --id GBTdnfD6s5Q --aio --ntrial 10
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_scrape_request.py -- --category channel --id UCBjOe-Trw6N8neQV7NUsfiA --aio --ntrial 2

    # line by line format
    export YT_SCRAPE_SERVICE_HOST=localhost &&
    export YT_SCRAPE_SERVICE_PORT=1443 && 
        ipy test_scrape_request.py -- \
        --category video \
        --id m6UNCJESYHM \
        --aio \
        --ntrial 10

Todo:
    - test number of videos/channels/comments scraped per second, 
        by scaling number of threads / containers on the server side
"""

import argparse
import asyncio
import os
from time import time

import grpc  # type: ignore[import]
import grpc.aio  # type: ignore[import]
from google.protobuf.json_format import MessageToDict, MessageToJson
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import (ChannelScrapingsStub,
                                      CommentScrapingsStub, VideoScrapingsStub)
from youtube_recommender.settings import (YOUTUBE_CHANNEL_PREFIX,
                                          YOUTUBE_VIDEO_PREFIX)

parser = argparse.ArgumentParser(description="cli parameters")
parser.add_argument(
    "--aio",
    action="store_true",
    help="run async RPCs",
)
parser.add_argument(
    "--id",
    type=str,
    default=None,
    help="id to scrape (Channel, Video)",
)
parser.add_argument(
    "--category",
    type=str,
    default="video",
    choices=list(map(str.lower, ScrapeCategory.keys())),
    help="ScrapeCategory to scrape",
)
parser.add_argument(
    "--ntrial",
    type=int,
    default=1,
    help="how often to run the request, for speed testing",
)


def main_blocking(args, cat: int, url: str):
    """Run main loop, blocking."""
    res = None
    for _ in range(args.ntrial):
        request = ScrapeRequest(
            id=0,
            category=cat,
            value=url,
        )
        res = client.Scrape(request)

    return res

async def main(args, cat: int, url: str):
    """Run main loop."""
    request = ScrapeRequest(
        id=0,
        category=cat,
        value=url,
    )

    cors = [client.Scrape(request) for i in range(args.ntrial)]

    return await asyncio.gather(*cors)


if __name__ == "__main__":
    host = os.environ.get("YT_SCRAPE_SERVICE_HOST", None)
    port = os.environ.get("YT_SCRAPE_SERVICE_PORT", 50051)
    assert host is not None
    assert port is not None

    addr: str = f"{host}:{port}"
    cli_args = parser.parse_args()
    print(f"{cli_args=}")

    assert cli_args.id is not None
    category: str = cli_args.category.upper()
    assert category in ScrapeCategory.keys()
    cat = getattr(ScrapeCategory, category)

    if cli_args.aio:
        grpc = grpc.aio

    channel = grpc.insecure_channel(addr)

    if cat == ScrapeCategory.CHANNEL:
        client = ChannelScrapingsStub(channel)
        url = "{}{}".format(YOUTUBE_CHANNEL_PREFIX, cli_args.id)
    elif cat == ScrapeCategory.VIDEO:
        client = VideoScrapingsStub(channel)
        url = "{}{}".format(YOUTUBE_VIDEO_PREFIX, cli_args.id)
    elif cat == ScrapeCategory.COMMENT:
        client = CommentScrapingsStub(channel)
        url = cli_args.id

    print(f"{url=}")

    t0 = time()

    if cli_args.aio:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(main(cli_args, cat=cat, url=url))

    else:
        res = main_blocking(cli_args, cat=cat, url=url)

    if cli_args.ntrial == 1:
        print(f"{res=}")

    # todo: update live progress

    # todo: remove test_channel_Scrape_Request, rename this file
    elapsed: float = time() - t0
    items_per_sec: float = cli_args.ntrial / elapsed
    print(f"{items_per_sec=:.2f} {category=}")

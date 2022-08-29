r"""test_scrape_request.py

Run:
    # run serve.py first
    # python serve.py, OR docker-compose build && docker-compose up -d scrape-service
    export YT_SCRAPE_SERVICE_HOST=localhost         && ipy test_scrape_request.py -- --category video   --id GBTdnfD6s5Q --aio --ntrial 10
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_scrape_request.py -- --category video   --id GBTdnfD6s5Q --aio --ntrial 10
    export YT_SCRAPE_SERVICE_HOST=192.168.178.46    && ipy test_scrape_request.py -- --category channel --id UCBjOe-Trw6N8neQV7NUsfiA --aio --ntrial 2

    # line by line format: video/comment
    export YT_SCRAPE_SERVICE_HOST=localhost &&
    export YT_SCRAPE_SERVICE_PORT=1443 && 
    export YT_SCRAPE_CERT_PATH=../../cert/nginx.cert && 
        ipy test_scrape_request.py -- \
        --category video \
        --id m6UNCJESYHM \
        --aio \
        --ntrial 10 \
        # --secure

    # line by line format: channel
    export YT_SCRAPE_SERVICE_HOST=localhost &&
    export YT_SCRAPE_SERVICE_PORT=1443 && 
    export YT_SCRAPE_CERT_PATH=../../cert/nginx.cert && 
        ipy test_scrape_request.py -- \
        --category channel \
        --id UCXPHFM88IlFn68OmLwtPmZA \
        --aio \
        --ntrial 10 \
        # --secure

Todo:
    - test number of videos/channels/comments scraped per second, 
        by scaling number of threads / containers on the server side
"""

import argparse
import asyncio
import logging
import os
from time import time
from typing import List

import grpc  # type: ignore[import]
import grpc.aio  # type: ignore[import]
from google.protobuf.json_format import MessageToDict, MessageToJson
from grpc import ssl_channel_credentials
from rarc_utils.sqlalchemy_base import (get_async_session, get_session,
                                        load_config)
from scrape_requests_pb2 import ScrapeCategory, ScrapeRequest
from scrape_requests_pb2_grpc import (ChannelScrapingsStub,
                                      CommentScrapingsStub, VideoScrapingsStub)
from youtube_recommender import config as config_dir
from youtube_recommender.db.helpers import (get_top_channels_with_comments,
                                            get_top_videos_by_channel_ids)
from youtube_recommender.settings import (YOUTUBE_CHANNEL_PREFIX,
                                          YOUTUBE_VIDEO_PREFIX)

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="cli parameters")
parser.add_argument(
    "--secure",
    action="store_true",
    help="secure gRPC channels with SSL",
)
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
parser.add_argument(
    "--cfg_file",
    type=str,
    default="postgres.cfg",
    help="cfg file of db to get video_ids from",
)

url_formats = {
    ScrapeCategory.CHANNEL: lambda x: "{}{}".format(YOUTUBE_CHANNEL_PREFIX, x),
    ScrapeCategory.VIDEO: lambda x: "{}{}".format(YOUTUBE_VIDEO_PREFIX, x),
    ScrapeCategory.COMMENT: lambda x: x,
}


def get_client(cat, chan):
    if cat == ScrapeCategory.CHANNEL:
        cl = ChannelScrapingsStub(chan)
    elif cat == ScrapeCategory.VIDEO:
        cl = VideoScrapingsStub(chan)
    elif cat == ScrapeCategory.COMMENT:
        cl = CommentScrapingsStub(chan)

    return cl


def construct_urls(args, cat, chan) -> List[str]:

    # assert cli_args.id is not None
    if args.id is None:
        # get random ids from db
        if cat == ScrapeCategory.CHANNEL:
            df = loop.run_until_complete(
                get_top_channels_with_comments(async_session, dropna=True)
            )
            ids = df.channel_id.sample(args.ntrial, replace=True).to_list()
        else:
            df = loop.run_until_complete(get_top_videos_by_channel_ids(async_session))
            ids = df.video_id.sample(args.ntrial, replace=True).to_list()
    else:
        ids = [args.id for i in range(args.ntrial)]

    urls = [url_formats[cat](x) for x in ids]

    if len(urls) < args.ntrial:
        logger.warning(
            f"less urls created than requested: {len(urls):,} < {args.ntrial:,}"
        )

    return urls


def main_blocking(cat: int, urls: List[str]):
    """Run main loop, blocking."""
    res = None
    for i, url in enumerate(urls):
        request = ScrapeRequest(
            id=i,
            category=cat,
            value=url,
        )
        res = client.Scrape(request)

    return res


async def main(cat: int, urls: List[str]):
    """Run main loop."""
    cors = [
        client.Scrape(
            ScrapeRequest(
                id=i,
                category=cat,
                value=url,
            )
        )
        for i, url in enumerate(urls)
    ]

    return await asyncio.gather(*cors)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    host = os.environ.get("YT_SCRAPE_SERVICE_HOST", None)
    port = os.environ.get("YT_SCRAPE_SERVICE_PORT", 50051)
    cert_path = os.environ.get("YT_SCRAPE_CERT_PATH", "/run/secrets/nginx.cert")

    cli_args = parser.parse_args()
    print(f"{cli_args=}")

    psql = load_config(
        db_name="youtube",
        cfg_file=cli_args.cfg_file,
        config_dir=config_dir,
        starts_with=True,
    )
    psession = get_session(psql)()
    async_session = get_async_session(psql)

    assert host is not None
    assert port is not None

    addr: str = f"{host}:{port}"

    category: str = cli_args.category.upper()
    assert category in ScrapeCategory.keys()
    cat = getattr(ScrapeCategory, category)

    if cli_args.aio:
        grpc = grpc.aio

    if cli_args.secure:
        with open(cert_path, "rb") as f:
            trusted_certs = f.read()
        credentials = ssl_channel_credentials(root_certificates=trusted_certs)
        channel = grpc.secure_channel(addr, credentials)
    else:
        channel = grpc.insecure_channel(addr)

    client = get_client(cat, channel)
    urls: List[str] = construct_urls(cli_args, cat, channel)

    print(f"{len(urls)=:,}")

    t0: float = time()

    if cli_args.aio:
        res = loop.run_until_complete(main(cat=cat, urls=urls))

    else:
        res = main_blocking(cat=cat, urls=urls)

    if cli_args.ntrial == 1:
        print(f"{res=}")

    # todo: update live progress

    # todo: use random video ids from DB instead of calling the same id 1000X times.

    # todo: remove test_channel_Scrape_Request, rename this file
    elapsed: float = time() - t0
    # items_per_sec: float = cli_args.ntrial / elapsed
    items_per_sec: float = len(res) / elapsed

    print(f"{items_per_sec=:.2f} {category=}")

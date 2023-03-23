#!/usr/bin/env python

from typing import Final, List

from setuptools import find_packages, setup

Requirements = List[str]

# requires: Final[Requirements] = []
requires: Final[Requirements] = [
    "yapic.json>=1.7.0",
    "pandas>=1.0.3",
    "timeago>=1.0.15",
    "sqlalchemy>=1.4.23",
    "google-api-python-client>=2.58.0",
    "youtube-transcript-api>=0.4.4",
    "langid>=1.1.6",
    "pyarrow",
    "pytube",
    "youtube_comment_downloader",
    # "cqlengine",
    "aiocache",
    # "aioredis==1.3.1",
    "jsonlines",
    "types-protobuf",
    "grpcio-tools",
    "grpc-interceptor~=0.12.0",
    "pytest",
]

dev_requires: Final[Requirements] = [
    "spacy",
    "gensim",
    "bertopic",
    "pre-commit",
    "spacytextblob",
]

setup(
    name="youtube_recommender",
    version="0.1.2",
    description="YouTube recommender - \
        data science project to extract recommendations from youtube video metadata",
    url="git@github.com:paulbroek/youtube-recommender.git",
    author="Paul Broek",
    author_email="pcbroek@paulbroek.nl",
    license="unlicense",
    install_requires=requires,
    extras_require={"dev": dev_requires},
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    zip_safe=False,
)

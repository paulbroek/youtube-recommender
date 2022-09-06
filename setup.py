#!/usr/bin/env python

from setuptools import find_packages, setup

# requires = []
requires = [
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
    "cqlengine",
    "aiocache",
    "aioredis==1.3.1",
    "jsonlines",
    "types-protobuf",
    "grpcio-tools",
    "grpc-interceptor~=0.12.0",
    "pytest",
]

dev_requires = [
    "spacy",
    "gensim",
    "bertopic",
    "pre-commit",
    "spacytextblob",
]

setup(
    name="youtube_recommender",
    version="0.1.0",
    description="YouTube recommender - \
        gives you recommended YouTube videos based on your watch history",
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

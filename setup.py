#!/usr/bin/env python

from setuptools import find_packages, setup

requires = []
# requires = [
#     "yapic.json>=1.7.0",
#     "pandas>=1.0.3",
#     "timeago>=1.0.15",
#     "sqlalchemy>=1.4.23",
#     "PyYAML>=5.4.1",
# ]

setup(
    name="youtube_recommender",
    version="0.0.6",
    description="YouTube recommender - \
        gives you recommended YouTube videos based on your watch history",
    url="git@github.com:paulbroek/youtube-recommender.git",
    author="Paul Broek",
    author_email="pcbroek@paulbroek.nl",
    license="unlicense",
    install_requires=requires,
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    zip_safe=False,
)

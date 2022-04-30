""" CLI tool to extract topics from youtube videos """

import argparse

import caption_finder as cf

from utils.misc import load_yaml

parser = argparse.ArgumentParser(description="Defining parameters")
parser.add_argument(
    "video_ids",
    type=str,
    nargs="+",
    help="The YouTube videos to extract captions from. Can be multiple.",
)
parser.add_argument(
    "--save_captions",
    action="store_true",
    default=False,
    help="Save captions to data/captions.feather",
)

args = parser.parse_args()

config = load_yaml("./config.yaml")


if __name__ == "__main__":

    video_ids = args.video_ids

    captions = cf.download_captions(video_ids)

    if args.save_captions:
        df = cf.captions_to_df(captions)

        df.to_feather("youtube-recommender/data/captions.feather")

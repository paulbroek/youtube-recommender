""" CLI tool to extract topics from youtube videos """

import argparse
import logging

import pandas as pd

from rarc_utils.log import setup_logger
import caption_finder as cf
from settings import VIDEOS_PATH, CAPTIONS_PATH

log_fmt = "%(asctime)s - %(module)-14s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  # name
logger = setup_logger(
    cmdLevel=logging.INFO, saveFile=0, savePandas=1, fmt=log_fmt
)  # DEBUG

parser = argparse.ArgumentParser(description="Defining parameters")
parser.add_argument(
    "video_ids",
    type=str,
    nargs="+",
    help="The YouTube videos to extract captions from. Can be multiple.",
)
parser.add_argument(
    "--from_feather",
    action="store_true",
    default=False,
    help=f"Import video ids from `{VIDEOS_PATH.as_posix()}`, created in main.py. ignores any manually passed video_ids",
)
parser.add_argument(
    "--save_captions",
    action="store_true",
    default=False,
    help=f"Save captions to `{CAPTIONS_PATH.as_posix()}`",
)

args = parser.parse_args()

if __name__ == "__main__":

    if args.from_feather:
        # check if file exists, or warn user to run main.py first
        vdf = pd.read_feather(VIDEOS_PATH)
        video_ids = vdf.video_id.to_list()
    else:
        video_ids = args.video_ids

    captions = cf.download_captions(video_ids)
    df = cf.captions_to_df(captions)

    if args.save_captions:

        df.to_feather(CAPTIONS_PATH)
        logger.info(f"saved {len(df):,} captions to {CAPTIONS_PATH.as_posix()}")

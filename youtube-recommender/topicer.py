""" CLI tool to extract topics from youtube videos """

import argparse
import logging
from pathlib import Path

from rarc_utils.log import setup_logger
import caption_finder as cf

log_fmt     = "%(asctime)s - %(module)-14s - %(lineno)-4s - %(funcName)-16s - %(levelname)-7s - %(message)s"  #name
logger      = setup_logger(cmdLevel=logging.INFO, saveFile=0, savePandas=1, fmt=log_fmt) # DEBUG

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

DATA_DIR = Path("youtube-recommender/data")
CAPTIONS_FILE = 'captions.feather'
CAPTIONS_PATH = DATA_DIR / CAPTIONS_FILE


if __name__ == "__main__":

    video_ids = args.video_ids

    captions = cf.download_captions(video_ids)
    df = cf.captions_to_df(captions)

    if args.save_captions:

        df.to_feather(CAPTIONS_PATH)
        logger.info(f"saved {len(df):,} captions to {CAPTIONS_PATH.as_posix()}")

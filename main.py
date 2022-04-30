#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:09:52 2020
@author: chrislovejoy
From: https://github.com/chris-lovejoy/YouTube-video-finder/

This module imports and calls the function to execute the API call
and print results to the console.
"""

import argparse
import yaml
import video_finder as vf
import caption_finder as cf

parser = argparse.ArgumentParser(description='Defining search parameters')
parser.add_argument('search_terms', type=str, nargs='+',
                    help='The terms to query. Can be multiple.')
parser.add_argument('--search-period', type=int, default=7,
                    help='The number of days to search for.')
args = parser.parse_args()


def load_yaml(filepath):
    """Import YAML config file."""
    with open(filepath, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


config = load_yaml('./config.yaml')

if __name__ == "__main__":
    # start_date_string = vf.get_start_date_string(args.search_period)
    # res = vf.search_each_term(args.search_terms, config['api_key'],
    #                     start_date_string)

    video_id = 'IUAHUEy1V0Q'
    res2, youtube_api = cf.list_captions(video_id, config['api_key'])

    # caption_id = res2['items'][0]['id']
    # caption = cf.download_caption(caption_id, youtube_api, tfmt='srt') # sbv

    captions = cf.download_caption2(video_id)
    caption_text = cf.captions_to_str(captions)

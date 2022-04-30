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
import video_finder as vf
from utils.misc import load_yaml

parser = argparse.ArgumentParser(description='Defining search parameters')
parser.add_argument('search_terms', type=str, nargs='+',
                    help='The terms to query. Can be multiple.')
parser.add_argument('--search-period', type=int, default=7,
                    help='The number of days to search for.')
args = parser.parse_args()

config = load_yaml('./config.yaml')

if __name__ == "__main__":
    start_date_string = vf.get_start_date_string(args.search_period)
    res = vf.search_each_term(args.search_terms, config['api_key'],
                        start_date_string)

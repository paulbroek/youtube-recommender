""" misc.py
miscelannous utility methods for youtube-recommender
"""

import yaml


def load_yaml(filepath):
    """Import YAML config file."""
    with open(filepath, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

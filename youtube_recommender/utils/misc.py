"""misc.py, miscelannous utility methods for youtube-recommender."""

import yaml

ENC = "utf8"

def load_yaml(filepath):
    """Import YAML config file."""
    with open(filepath, "r", encoding=ENC) as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    return None

"""misc.py, miscelannous utility methods for youtube-recommender."""

import configparser
from pathlib import Path

import yaml
from rarc_utils.misc import AttrDict
from youtube_recommender import config as config_dir

ENC = "utf8"


def load_yaml(filepath):
    """Import YAML config file."""
    with open(filepath, "r", encoding=ENC) as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    return None


def load_config():
    """Load config.

    ugly way of retrieving postgres cfg file
    """
    p = Path(config_dir.__file__)
    cfgFile = p.with_name("postgres.cfg")

    parser = configparser.ConfigParser()
    parser.read(cfgFile)
    assert "psql" in parser, f"'psql' not in {cfgFile=}"
    psql = AttrDict(parser["psql"])
    assert psql["db"] == "youtube"  # do not overwrite existing other db

    return psql

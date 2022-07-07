import configparser
from pathlib import Path

from rarc_utils.misc import AttrDict
from youtube_recommender import config as config_dir


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

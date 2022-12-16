import configparser
import os
from pathlib import Path

from rarc_utils.misc import AttrDict
from youtube_recommender import config as config_dir


def load_config():
    """Load config.

    ugly way of retrieving postgres cfg file
    """
    releaseMode = os.environ.get("RELEASE_MODE", "DEVELOPMENT")
    # take from secrets dur if running in production: kubernetes
    configDir = config_dir.__file__ if releaseMode == "DEVELOPMENT" else "/run/secrets"

    p = Path(configDir)
    cfgFile = p.with_name("postgres.cfg")

    parser = configparser.ConfigParser()
    parser.read(cfgFile)
    assert "psql" in parser, f"'psql' not in {cfgFile=}"
    psql = AttrDict(parser["psql"])
    assert psql["db"] == "youtube"  # do not overwrite existing other db

    return psql

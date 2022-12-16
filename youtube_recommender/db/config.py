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
    cfgFile = "postgres.cfg"
    cfgPath = (
        Path(config_dir.__file__).with_name(cfgFile)
        if releaseMode == "DEVELOPMENT"
        else Path("/run/secrets") / cfgFile
    )

    parser = configparser.ConfigParser()
    parser.read(cfgPath)
    assert "psql" in parser, f"'psql' not in {cfgPath=}"
    psql = AttrDict(parser["psql"])
    assert psql["db"] == "youtube"  # do not overwrite existing other db

    return psql

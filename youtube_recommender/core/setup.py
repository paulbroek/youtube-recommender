"""setup.py.

initializing module settings
"""

from dotenv import load_dotenv
from scrape_utils.core.config_env_file import config_env

# from .config import psqlConfig
from .config import Settings

PYTHON_ENV, ENV_FILE = config_env()
load_dotenv(ENV_FILE)
settings = Settings()
# psql_config = psqlConfig()

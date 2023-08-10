from typing import List

from pydantic import BaseSettings


# class psqlConfig(BaseSettings):
class Settings(BaseSettings):
    # pg_host: str
    # pg_port: int
    # pg_user: str
    # pg_passwd: str
    # pg_db: str

    # Base
    api_v1_prefix: str
    debug: bool
    project_name: str
    version: str
    description: str
    data_dir: str

    # Database
    db_host: str
    db_port: int
    db_pass: str
    db_name: str
    db_connection_str: str
    db_async_connection_str: str
    db_exclude_tables: List[str]

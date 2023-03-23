from pydantic import BaseSettings


class psqlConfig(BaseSettings):
    pg_host: str
    pg_port: int
    pg_user: str
    pg_passwd: str
    pg_db: str

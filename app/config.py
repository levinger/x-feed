from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATA_DIR: str = "./data"
    FETCH_INTERVAL_MINUTES: int = 15
    TWEETS_PER_KEYWORD: int = 50
    FEED_PAGE_SIZE: int = 50

    class Config:
        env_file = ".env"

    def get_db_path(self) -> str:
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        return f"{self.DATA_DIR}/news_feed.db"

    def get_accounts_db_path(self) -> str:
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        return f"{self.DATA_DIR}/accounts.db"


settings = Settings()

# support both pydantic v1 (<2) and v2 where BaseSettings moved to pydantic-settings
try:
    from pydantic import BaseSettings, AnyUrl
except ImportError:  # pydantic v2+
    from pydantic_settings import BaseSettings
    from pydantic import AnyUrl


class Settings(BaseSettings):
    database_url: AnyUrl
    poll_seconds: int = 60
    status_url: str = "https://live.radionostalgia.ro:8443/status-json.xsl"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

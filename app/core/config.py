from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MYSQL_URL: str = "mysql+pymysql://root:password@localhost/prerak"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RUNTIME_MODE: str = "ollama"
    OLLAMA_URL: str = "http://localhost:11434"

    class Config:
        env_file = ".env"

settings = Settings()

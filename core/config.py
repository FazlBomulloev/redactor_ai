from pydantic import BaseModel

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# Загрузка переменных окружения из файла .env
load_dotenv()


class DatabaseConfig(BaseModel):
    url: str


class AdmConfig(BaseModel):
    tg_id: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_nested_delimiter="__",
    )
    db: DatabaseConfig
    su: AdmConfig
    channel__link: int

def reload_settings():
    """
    Перезагружает .env и обновляет глобальные настройки.
    """
    load_dotenv(dotenv_path=".env", override=True)
    global settings
    settings = Settings()

def update_channel_settings():
    """
    Обновляет настройки канала и уведомляет планировщик
    """
    reload_settings()
    # Импортируем здесь, чтобы избежать циклических импортов
    try:
        from utils.shedule import update_channel_settings
        import asyncio
        asyncio.create_task(update_channel_settings())
    except Exception as e:
        print(f"Error updating channel settings: {e}")


settings = Settings()

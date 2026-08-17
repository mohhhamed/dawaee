"""قراءة الإعدادات من ملف .env مع قيم افتراضية آمنة."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # وضع التشغيل: mock (تجريبي) أو live (حقيقي)
    APP_MODE: str = "mock"

    DATABASE_URL: str = "sqlite:///./data/social.db"

    META_APP_ID: str = ""
    META_APP_SECRET: str = ""

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    IMAGE_API_KEY: str = ""
    VISION_API_KEY: str = ""

    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = ""

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    @property
    def is_mock(self) -> bool:
        """النظام يعمل تجريبيًا إذا لم يُطلب live صراحةً."""
        return self.APP_MODE.lower() != "live"


settings = Settings()

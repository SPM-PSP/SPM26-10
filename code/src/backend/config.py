import os

from dotenv import load_dotenv


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_url:
        return explicit_url

    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "123456")
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "educational_platform")

    return f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


class Settings:
    # 数据库配置
    DATABASE_URL: str = _build_database_url()

    # LLM 配置
    LLM_MODE: str = os.getenv("LLM_MODE", "local").lower()  # local | api | hybrid
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "dashscope").lower()
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "").strip()
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
    LLM_API_MODEL: str = os.getenv("LLM_API_MODEL", "qwen-plus").strip()
    LLM_API_TIMEOUT_SECONDS: int = int(os.getenv("LLM_API_TIMEOUT_SECONDS", "120"))

    # Embedding / RAG 配置
    EMBEDDING_MODE: str = os.getenv("EMBEDDING_MODE", "local").lower()  # local | api
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local").lower()
    EMBEDDING_API_BASE_URL: str = os.getenv("EMBEDDING_API_BASE_URL", "").strip()
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "").strip()
    EMBEDDING_API_MODEL: str = os.getenv("EMBEDDING_API_MODEL", "").strip()

    def uses_remote_llm(self) -> bool:
        return self.LLM_MODE in {"api", "hybrid"}

    def uses_local_llm(self) -> bool:
        return self.LLM_MODE == "local"


settings = Settings()

import os

from dotenv import load_dotenv


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


class Settings:
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+aiomysql://root:123456@localhost:3306/educational_platform")

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

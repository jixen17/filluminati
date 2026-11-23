from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    groq_api_key: str = ""
    llm_model: str = ""
    frontend_url: str = "http://localhost:5173"
    allowed_hosts: str = "localhost,127.0.0.1"
    database_url: str = f"sqlite:///{BASE_DIR / 'formpilot.db'}"
    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    debug_routes: bool = True

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
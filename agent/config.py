"""All settings come from environment variables (or a .env file). Edit .env, not this file."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    text_model: str = os.getenv("TEXT_MODEL", "gpt-4.1")
    image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-1")
    make_images: bool = _bool("MAKE_IMAGES", True)
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "90"))

    # Storage. Relative paths are resolved from the project folder.
    data_dir: str = os.path.abspath(os.getenv("DATA_DIR", "data"))      # database, uploads
    output_dir: str = os.path.abspath(os.getenv("OUTPUT_DIR", "output"))  # drafts per run

    # Optional HTTP Basic password for the web UI and API. Leave empty for local use.
    app_password: str = os.getenv("APP_PASSWORD", "")


settings = Settings()

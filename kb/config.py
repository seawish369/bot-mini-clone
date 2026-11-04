import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

HELP_CENTER_URL = "https://support.optisigns.com"
LOCALE = "en-us"
OUTPUT_DIR = Path("articles")
MODEL = "gpt-5-mini"
LOG_LEVEL = "INFO"
DEFAULT_VECTOR_STORE_NAME = "optibot-help-center"


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    vector_store_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv() 
        return cls(
            api_key=(os.getenv("API_KEY") or "").strip(),
            vector_store_name=os.getenv("VECTOR_STORE_NAME") or DEFAULT_VECTOR_STORE_NAME,
        )

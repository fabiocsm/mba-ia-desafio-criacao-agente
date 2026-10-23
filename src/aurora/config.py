"""Configuração sem segredos versionados.

Nomes aceitos: GOOGLE_API_KEY, GEMINI_MODEL e AURORA_DATA_DIR.
Valores vazios usam os defaults documentados. Caminhos relativos de dados
são resolvidos a partir da raiz do repositório, não do diretório corrente.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "aurora"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_DATA_DIR = "var"


def repo_root() -> Path:
    """Raiz do repositório, estável independentemente do cwd."""
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=repo_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str = ""
    gemini_model: str = DEFAULT_MODEL
    aurora_data_dir: str = DEFAULT_DATA_DIR

    @field_validator("gemini_model", mode="before")
    @classmethod
    def _modelo(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_MODEL
        return value

    @field_validator("aurora_data_dir", mode="before")
    @classmethod
    def _diretorio(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_DATA_DIR
        return value

    @property
    def data_dir(self) -> Path:
        path = Path(self.aurora_data_dir).expanduser()
        if not path.is_absolute():
            path = repo_root() / path
        return path.resolve()

    @property
    def business_db_path(self) -> Path:
        return self.data_dir / "aurora.sqlite3"

    @property
    def adk_db_path(self) -> Path:
        return self.data_dir / "adk.sqlite3"

    @property
    def dados_dir(self) -> Path:
        return repo_root() / "dados"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def export_api_key(settings: Settings | None = None) -> None:
    """Disponibiliza a chave ao SDK sem registrá-la em log."""
    resolved = settings if settings is not None else get_settings()
    if resolved.google_api_key:
        os.environ["GOOGLE_API_KEY"] = resolved.google_api_key

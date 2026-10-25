"""App ADK resumível, com o principal e os três especialistas na mesma árvore."""

from __future__ import annotations

from google.adk.apps.app import App
from google.adk.apps.app import ResumabilityConfig

from aurora.agents.principal import build_principal
from aurora.config import APP_NAME
from aurora.regulamento.parser import reconstruir_indice


def build_app() -> App:
    reconstruir_indice()
    return App(
        name=APP_NAME,
        root_agent=build_principal(),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )

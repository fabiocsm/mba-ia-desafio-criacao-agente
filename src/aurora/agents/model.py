"""Repetição limitada da chamada Gemini, sem repetir o Runner ou as tools."""

from google.adk.models.google_llm import Gemini
from google.genai import types

from aurora.config import get_settings


def build_model() -> Gemini:
    return Gemini(
        model=get_settings().gemini_model,
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=1,
            max_delay=8,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    )

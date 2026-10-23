"""Confirma acesso ao modelo configurado e uma chamada de função simples.

Não imprime a chave. Não consulta nem afirma quota do projeto.
"""

from __future__ import annotations

import sys

from google import genai
from google.genai import types

from aurora.config import export_api_key
from aurora.config import get_settings


def ping() -> dict[str, str]:
    """Confirma que a chamada de função está disponível."""
    return {"status": "ok"}


def _sanitizar(texto: str, segredo: str) -> str:
    if segredo:
        texto = texto.replace(segredo, "[redacted]")
    return texto


def _chamou_ping(response, chat) -> bool:
    conteudos = list(getattr(response, "automatic_function_calling_history", None) or [])
    if chat is not None:
        conteudos.extend(chat.get_history(curated=False))
    for conteudo in conteudos:
        for parte in getattr(conteudo, "parts", None) or []:
            chamada = getattr(parte, "function_call", None)
            if chamada is not None and getattr(chamada, "name", "") == "ping":
                return True
    for chamada in getattr(response, "function_calls", None) or []:
        if getattr(chamada, "name", "") == "ping":
            return True
    return False


def main() -> int:
    settings = get_settings()
    export_api_key(settings)
    if not settings.google_api_key:
        print("GOOGLE_API_KEY ausente. Preencha .env sem colar a chave no terminal.")
        return 1
    print(f"modelo={settings.gemini_model}")
    try:
        client = genai.Client(
            api_key=settings.google_api_key,
            http_options=types.HttpOptions(timeout=120_000),
        )
        chat = client.chats.create(
            model=settings.gemini_model,
            config=types.GenerateContentConfig(
                tools=[ping],
                temperature=0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=False,
                    maximum_remote_calls=2,
                ),
            ),
        )
        response = chat.send_message("Chame a função ping exatamente uma vez.")
    except Exception as exc:
        print(_sanitizar(f"erro={type(exc).__name__}: {exc}", settings.google_api_key))
        return 1
    if not _chamou_ping(response, chat):
        print("chamada_de_funcao=nao")
        return 1
    print("chamada_de_funcao=sim")
    return 0


if __name__ == "__main__":
    sys.exit(main())

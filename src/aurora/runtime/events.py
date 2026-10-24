"""Leitura integral dos eventos persistidos. Não filtra nem regrava.

Chamadas, resultados e transferências permanecem completos, inclusive o
trecho autorizado do regulamento. Este módulo não recebe o índice e não
remove evento para esconder consulta.
"""

from __future__ import annotations

from google.adk.events.event import Event


def texto_visivel(event: Event) -> str:
    content = event.content
    if content is None or not content.parts:
        return ""
    partes: list[str] = []
    for part in content.parts:
        texto = getattr(part, "text", None)
        if texto:
            partes.append(texto)
    return "".join(partes).strip()


def coletar_resposta(eventos: list[Event]) -> str:
    """Junta o texto final destinado ao morador, sem raciocínio interno."""
    finais: list[str] = []
    quaisquer: list[str] = []
    for evento in eventos:
        if evento.author == "user" or evento.partial:
            continue
        texto = texto_visivel(evento)
        if not texto:
            continue
        quaisquer.append(texto)
        if evento.is_final_response():
            finais.append(texto)
    return "\n".join(finais or quaisquer).strip()


def serializar_eventos(eventos: list[Event]) -> list[dict]:
    return [evento.model_dump(mode="json") for evento in eventos]

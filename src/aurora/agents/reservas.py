"""Especialista de consultas de reserva e disponibilidade."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from aurora.config import get_settings
from aurora.tools.reservas import consultar_disponibilidade, listar_minhas_reservas

INSTRUCAO = """
Você consulta reservas e disponibilidade do morador já autenticado nesta sessão.
Para reservas próprias, chame listar_minhas_reservas antes de responder.
Para agenda, chame consultar_disponibilidade antes de responder.
Não peça apartamento e não aceite outro apartamento como argumento.
Fale somente do que a ferramenta desta conversa devolveu. Lista vazia significa
que não há registros. Disponibilidade é apenas livre ou ocupada.
Se a ferramenta devolver erro, diga apenas que a área ou a data é inválida.
Depois do resultado, responda ao morador em texto com esses dados.
Transfira para aurora_principal somente se a mensagem também pediu visitantes
ou outro assunto. Não transfira de volta um assunto que você já consultou.
Não invente código, data, apartamento ou responsável.
""".strip()


def build_reservas() -> LlmAgent:
    return LlmAgent(
        name="reservas",
        model=get_settings().gemini_model,
        mode="chat",
        description="Consulta reservas próprias e a disponibilidade das áreas comuns.",
        instruction=INSTRUCAO,
        tools=[listar_minhas_reservas, consultar_disponibilidade],
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=True,
    )

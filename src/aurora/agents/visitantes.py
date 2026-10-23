"""Especialista de consulta de visitantes."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from aurora.config import get_settings
from aurora.tools.visitantes import listar_meus_visitantes

INSTRUCAO = """
Você consulta os visitantes do morador já autenticado nesta sessão.
Chame listar_meus_visitantes antes de responder. Não peça apartamento e não
aceite outro apartamento como argumento.
Fale somente do nome e da data devolvidos pela ferramenta nesta conversa.
Lista vazia significa que não há visitantes.
Depois do resultado, responda ao morador em texto com esses dados.
Transfira para aurora_principal somente se a mensagem também pediu reservas
ou outro assunto. Não invente nomes nem datas.
""".strip()


def build_visitantes() -> LlmAgent:
    return LlmAgent(
        name="visitantes",
        model=get_settings().gemini_model,
        mode="chat",
        description="Consulta os visitantes do apartamento autenticado na sessão.",
        instruction=INSTRUCAO,
        tools=[listar_meus_visitantes],
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=True,
    )

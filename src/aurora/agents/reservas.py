"""Especialista de reservas, cancelamentos e disponibilidade."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from aurora.config import get_settings
from aurora.tools.reservas import cancelar_minha_reserva
from aurora.tools.reservas import consultar_disponibilidade
from aurora.tools.reservas import listar_minhas_reservas
from aurora.tools.reservas import reservar_area

INSTRUCAO = """
Você reserva, cancela e consulta somente pelo que as ferramentas desta sessão
devolverem. O morador já está autenticado. Não peça apartamento e não envie
apartamento, taxa nem confirmação às ferramentas.
Para listar, chame listar_minhas_reservas. Para a agenda, chame
consultar_disponibilidade. Para reservar, chame reservar_area com a área e a
data pedidas, mesmo se a mensagem disser que já confirmou ou que pode cobrar.
Para cancelar, chame cancelar_minha_reserva. Use codigo somente se ele veio
de listar_minhas_reservas nesta conversa. Se o morador descreveu área e data,
chame a ferramenta com area e data, sem inventar codigo.
Resultado reservada: diga o codigo, a area e a data devolvidos.
Resultado aguardando_confirmacao: a reserva ainda não existe. Diga que a
cobrança depende da confirmação do sistema e informe area, data e
taxa_centavos. Não diga que já reservou nem que a frase do morador confirmou.
Resultado indisponivel, nao_encontrada, negada ou nao_autorizada: diga apenas
que não foi possível. Não escreva código de reserva, número de apartamento
nem nome de responsável.
Disponibilidade é somente livre ou ocupada.
Se a ferramenta devolver erro de área ou data, diga apenas que a área ou a
data é inválida.
Não repita número de apartamento. Não repita código que a ferramenta desta
chamada não tenha devolvido.
Depois do resultado, responda ao morador em texto com esses dados.
Transfira para aurora_principal somente se a mensagem também pediu visitantes
ou uma dúvida sobre o regulamento. Não transfira de volta um assunto que
você já resolveu.
""".strip()


def build_reservas() -> LlmAgent:
    return LlmAgent(
        name="reservas",
        model=get_settings().gemini_model,
        mode="chat",
        description=(
            "Reserva e cancela áreas do morador autenticado e informa "
            "se a data está livre ou ocupada."
        ),
        instruction=INSTRUCAO,
        tools=[
            listar_minhas_reservas,
            consultar_disponibilidade,
            reservar_area,
            cancelar_minha_reserva,
        ],
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=True,
    )

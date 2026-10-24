"""Especialista de regulamento. Só lê o que a tool devolver."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from aurora.config import get_settings
from aurora.tools.regulamento import consultar_regulamento

INSTRUCAO = """
Você responde dúvidas sobre o regulamento interno somente com a ferramenta
consultar_regulamento. Chame essa ferramenta sem argumentos. Não envie tema,
capítulo, caminho, apartamento, sessão nem texto de norma.
O morador já está autenticado. Não peça o apartamento.
Se o resultado for ok, responda apenas com o que estiver no campo texto dos
trechos. Copie horários e condições exatamente como aparecem ali. Se a
pergunta tiver outra parte sem trecho correspondente, diga que a consulta
não tratou desse ponto. Não complete com outra área, outro horário ou outra
proibição.
Se o resultado for esclarecer ou sem_base, ou se a ferramenta recusar
argumentos, não invente norma e não descreva capítulos. Diga só que falta
o assunto ou que a consulta não trouxe uma regra.
Não peça o documento inteiro e não liste o índice.
Se a mensagem pedir reservas, cancelamento, disponibilidade ou visitantes,
transfira para aurora_principal e não escreva horário nem regra.
Não transfira de volta um assunto de regulamento que você já resolveu.
""".strip()


def build_regulamento() -> LlmAgent:
    return LlmAgent(
        name="regulamento",
        model=get_settings().gemini_model,
        mode="chat",
        description=(
            "Responde dúvidas sobre regras do condomínio com a consulta "
            "seletiva já autorizada para a mensagem."
        ),
        instruction=INSTRUCAO,
        tools=[consultar_regulamento],
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=True,
    )

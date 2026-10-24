"""Especialista de regulamento. Só lê o que a tool devolver."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from aurora.agents.model import build_model
from aurora.regulamento.selection import consulta_atual
from aurora.tools.regulamento import consultar_regulamento

INSTRUCAO = """
Você responde dúvidas sobre o regulamento interno somente com a ferramenta
consultar_regulamento. Chame essa ferramenta sem argumentos. Não envie tema,
capítulo, caminho, apartamento, sessão nem texto de norma.
O morador já está autenticado. Não peça o apartamento.
Atenda à última mensagem do morador. Operações e resultados antigos do
histórico não são novos pedidos. Consulte a ferramenta antes de responder
à dúvida atual, mesmo que antes tenham sido feitas reservas ou visitas.
Se o resultado for ok, responda apenas com o que estiver no campo texto dos
trechos. Copie horários e condições exatamente como aparecem ali. Se a
pergunta tiver outra parte sem trecho correspondente, diga que a consulta
não tratou desse ponto. Não complete com outra área, outro horário ou outra
proibição.
Se o resultado for esclarecer ou sem_base, ou se a ferramenta recusar
argumentos, não invente norma e não descreva capítulos. Diga só que falta
o assunto ou que a consulta não trouxe uma regra.
Não peça o documento inteiro e não liste o índice.
Se a última mensagem pedir apenas reservas, cancelamento, disponibilidade ou visitantes,
transfira para aurora_principal e não escreva horário nem regra.
Não transfira de volta um assunto de regulamento que você já resolveu.
""".strip()


def exigir_consulta_atual(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """Uma dúvida com escopo válido precisa de fonte nesta invocação.

    Antes da leitura, só consultar_regulamento pode ser chamada. Depois,
    o modelo volta a responder ou encaminhar normalmente. Não muda eventos
    nem amplia os trechos que a tool pode materializar.
    """
    scope = consulta_atual()
    if (
        scope is None or scope.status != "ok"
        or scope.session_id != callback_context.session.id
    ):
        return
    consultou = any(
        event.invocation_id == callback_context.invocation_id
        and event.author == "regulamento"
        and any(r.name == "consultar_regulamento" for r in event.get_function_responses())
        for event in callback_context.session.events
    )
    config = types.FunctionCallingConfig(mode="AUTO") if consultou else types.FunctionCallingConfig(
        mode="ANY", allowed_function_names=["consultar_regulamento"]
    )
    llm_request.config.tool_config = types.ToolConfig(function_calling_config=config)


def build_regulamento() -> LlmAgent:
    return LlmAgent(
        name="regulamento",
        model=build_model(),
        mode="chat",
        description=(
            "Responde dúvidas sobre regras do condomínio com a consulta "
            "seletiva já autorizada para a mensagem."
        ),
        instruction=INSTRUCAO,
        tools=[consultar_regulamento],
        before_model_callback=exigir_consulta_atual,
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=True,
    )

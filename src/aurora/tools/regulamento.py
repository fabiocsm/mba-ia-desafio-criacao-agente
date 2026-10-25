"""Tool sem argumentos do modelo. Só materializa o escopo já autorizado."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from aurora.regulamento.parser import RegulamentoEstruturaError
from aurora.regulamento.parser import materializar
from aurora.regulamento.selection import consulta_atual
from aurora.tools.context import IdentidadeIndisponivel
from aurora.tools.context import resolve_identity

logger = logging.getLogger(__name__)

_DESCRICAO = (
    "Recupera os trechos do regulamento já autorizados para a mensagem "
    "atual do morador. Não informe tema, capítulo, caminho, apartamento "
    "nem sessão."
)


def _vazio(status: str) -> dict[str, Any]:
    return {"status": status, "trechos": []}


def consultar(tool_context: ToolContext) -> dict[str, Any]:
    """Confere sessão, nonce da execução e o conjunto fechado. Não relê a fonte inteira no retorno."""
    try:
        identidade = resolve_identity(tool_context)
    except IdentidadeIndisponivel:
        return _vazio("esclarecer")
    scope = consulta_atual()
    if (
        scope is None
        or not scope.execution_nonce
        or scope.session_id != identidade.session_id
    ):
        return _vazio("esclarecer")
    if scope.status != "ok":
        return _vazio(scope.status)
    try:
        trechos = materializar(scope.unidades)
    except RegulamentoEstruturaError:
        logger.error("Falha estrutural ao materializar trecho autorizado.")
        return _vazio("esclarecer")
    if not trechos:
        return _vazio("sem_base")
    return {"status": "ok", "trechos": trechos}


class ConsultarRegulamentoTool(BaseTool):
    """Schema sem parâmetros. Argumento extra não seleciona unidade."""

    def __init__(self) -> None:
        super().__init__(name="consultar_regulamento", description=_DESCRICAO)

    def _get_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        )

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict[str, Any]:
        if args:
            return {"erro": "Argumentos não aceitos."}
        return consultar(tool_context)


consultar_regulamento = ConsultarRegulamentoTool()

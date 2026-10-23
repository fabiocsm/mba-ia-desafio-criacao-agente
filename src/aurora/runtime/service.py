"""Conversa persistida. A identidade vem do repositório, não do cliente.

Pendências saem do banco de negócio. Aprovar ou negar passa pela rota de
confirmação, que retoma o Runner. Startup só reconcilia metadados.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import aclosing

from google.adk.agents.run_config import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.events.event import Event
from google.genai import types

from aurora.config import APP_NAME
from aurora.config import export_api_key
from aurora.config import get_settings
from aurora.errors import ApartamentoInexistente
from aurora.errors import ConfirmacaoConflito
from aurora.errors import ExecucaoExpirada
from aurora.errors import RetomadaIncompleta
from aurora.errors import SessaoInexistente
from aurora.runtime.app import build_app
from aurora.runtime.confirmacoes import ConfirmationCoordinator
from aurora.runtime.confirmacoes import retomada_persistida
from aurora.runtime.events import coletar_resposta
from aurora.runtime.runner import AuroraRunner
from aurora.runtime.events import serializar_eventos
from aurora.runtime.sessions import OrderedDatabaseSessionService
from aurora.runtime.sessions import adk_database_url
from aurora.runtime.sessions import tune_sqlite
from aurora.schemas import ConfirmacaoPendente
from aurora.schemas import MensagemResponse
from aurora.storage.confirmacoes import DecisaoRegistrada
from aurora.storage.confirmacoes import consumida
from aurora.storage.confirmacoes import decide
from aurora.storage.confirmacoes import despachos_recuperar
from aurora.storage.confirmacoes import list_pending
from aurora.storage.confirmacoes import marcar_concluido
from aurora.storage.confirmacoes import publish_from_event
from aurora.storage.confirmacoes import registrar_executor
from aurora.storage.confirmacoes import registrar_falha
from aurora.storage.confirmacoes import sessoes_preparando
from aurora.storage.database import dispose_engine
from aurora.storage.database import get_engine
from aurora.storage.identity import criar_sessao_coordenada
from aurora.storage.identity import obter_identidade
from aurora.storage.reservas import executar_reserva_paga
from aurora.storage.reservas import validar_parametros_reserva
from aurora.storage.seed import initialize_storage

logger = logging.getLogger(__name__)

RUN_TIMEOUT_SECONDS = 120

_RUN_CONFIG = RunConfig(
    streaming_mode=StreamingMode.NONE,
    max_llm_calls=20,
)


def registrar_acoes() -> None:
    registrar_executor(
        "reservar_area",
        validar=validar_parametros_reserva,
        executar=executar_reserva_paga,
    )


registrar_acoes()


class AuroraRuntime:
    def __init__(self, session_service: OrderedDatabaseSessionService, runner: AuroraRunner):
        self.session_service = session_service
        self.runner = runner
        self.coordinator = ConfirmationCoordinator(runner)
        self._guard = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = {}

    @classmethod
    async def start(cls) -> AuroraRuntime:
        settings = get_settings()
        export_api_key(settings)
        initialize_storage(get_engine(), settings.dados_dir)
        registrar_acoes()
        session_service = OrderedDatabaseSessionService(
            adk_database_url(settings.adk_db_path)
        )
        tune_sqlite(session_service)
        await session_service.prime_timestamps()
        runner = AuroraRunner(
            app=build_app(),
            session_service=session_service,
            auto_create_session=False,
        )
        runtime = cls(session_service, runner)
        await runtime.reconciliar_metadados()
        logger.info("Modelo configurado: %s", settings.gemini_model)
        logger.info("Diretório de dados: %s", settings.data_dir)
        return runtime

    async def aclose(self) -> None:
        await self.session_service.close()
        dispose_engine()

    async def _lock(self, session_id: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[session_id] = lock
            return lock

    async def criar_sessao(self, apartamento: str) -> str:
        try:
            return await criar_sessao_coordenada(
                get_engine(),
                self.session_service,
                apartamento,
            )
        except ApartamentoInexistente:
            raise
        except Exception:
            logger.exception("Falha ao criar sessão.")
            raise

    async def _exigir_adk(self, session_id: str):
        if obter_identidade(get_engine(), session_id) is None:
            raise SessaoInexistente
        adk_session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )
        if adk_session is None:
            raise SessaoInexistente
        return adk_session

    async def reconciliar_metadados(self) -> None:
        """Publica propostas cujo evento ADK já existe. Não chama o Runner."""
        for session_id in sessoes_preparando():
            await self._publicar_eventos(session_id)

    async def _publicar_eventos(self, session_id: str) -> None:
        try:
            adk_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=session_id,
                session_id=session_id,
            )
        except Exception as exc:
            logger.error("Falha ao ler eventos para correlacao (%s)", type(exc).__name__)
            return
        if adk_session is None:
            return
        for evento in adk_session.events:
            publish_from_event(evento, session_id)

    def _envelope(self, session_id: str, resposta: str) -> MensagemResponse:
        return MensagemResponse(
            resposta=resposta,
            confirmacoes_pendentes=[
                ConfirmacaoPendente.model_validate(item)
                for item in list_pending(session_id)
            ],
        )

    async def _executar(
        self,
        session_id: str,
        mensagem: types.Content,
        *,
        invocation_id: str | None = None,
    ) -> list[Event]:
        recebidos: list[Event] = []
        deadline = asyncio.timeout(RUN_TIMEOUT_SECONDS)
        try:
            async with deadline:
                async with aclosing(
                    self.runner.run_async(
                        user_id=session_id,
                        session_id=session_id,
                        invocation_id=invocation_id,
                        new_message=mensagem,
                        run_config=_RUN_CONFIG,
                    )
                ) as eventos:
                    async for evento in eventos:
                        recebidos.append(evento)
        except TimeoutError:
            if not deadline.expired():
                raise
            raise ExecucaoExpirada from None
        return recebidos

    async def _retomar(self, decisao: DecisaoRegistrada) -> list[Event]:
        recebidos: list[Event] = []
        deadline = asyncio.timeout(RUN_TIMEOUT_SECONDS)
        try:
            async with deadline:
                async for evento in self.coordinator.resume(decisao, _RUN_CONFIG):
                    recebidos.append(evento)
        except TimeoutError:
            registrar_falha(decisao.proposta_id, "ExecucaoExpirada")
            if not deadline.expired():
                raise
            raise ExecucaoExpirada from None
        except Exception as exc:
            registrar_falha(decisao.proposta_id, type(exc).__name__)
            raise
        persistidos = await self._exigir_adk(decisao.session_id)
        if self.coordinator.autores_divergentes(recebidos, decisao.author):
            registrar_falha(decisao.proposta_id, "author_divergente")
        if consumida(decisao.proposta_id) and retomada_persistida(
            persistidos.events, decisao
        ):
            marcar_concluido(decisao.proposta_id)
            return recebidos
        registrar_falha(decisao.proposta_id, "retomada_incompleta")
        raise RetomadaIncompleta

    async def _recuperar_despachos(self, session_id: str) -> None:
        for decisao in despachos_recuperar(session_id):
            persistidos = await self._exigir_adk(session_id)
            if consumida(decisao.proposta_id) and retomada_persistida(
                persistidos.events, decisao
            ):
                marcar_concluido(decisao.proposta_id)
                continue
            await self._retomar(decisao)

    async def enviar_mensagem(self, session_id: str, texto: str) -> MensagemResponse:
        async with await self._lock(session_id):
            await self._exigir_adk(session_id)
            await self._recuperar_despachos(session_id)
            recebidos = await self._executar(
                session_id,
                types.Content(role="user", parts=[types.Part(text=texto)]),
            )
            await self._publicar_eventos(session_id)
            return self._envelope(session_id, coletar_resposta(recebidos))

    async def confirmar(
        self,
        session_id: str,
        proposta_id: str,
        confirmado: bool,
    ) -> MensagemResponse:
        async with await self._lock(session_id):
            await self._exigir_adk(session_id)
            try:
                decisao = decide(session_id, proposta_id, confirmado)
            except ConfirmacaoConflito:
                raise
            recebidos = await self._retomar(decisao)
            return self._envelope(session_id, coletar_resposta(recebidos))

    async def listar_eventos(self, session_id: str) -> list[dict]:
        adk_session = await self._exigir_adk(session_id)
        return serializar_eventos(adk_session.events)

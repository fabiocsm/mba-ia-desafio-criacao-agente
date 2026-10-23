"""Conversa persistida. A identidade vem do repositório, não do cliente."""

from __future__ import annotations

import asyncio
import logging
from contextlib import aclosing

from google.adk.agents.run_config import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.genai import types

from aurora.config import APP_NAME
from aurora.config import export_api_key
from aurora.config import get_settings
from aurora.errors import ApartamentoInexistente
from aurora.errors import ExecucaoExpirada
from aurora.errors import SessaoInexistente
from aurora.runtime.app import build_app
from aurora.runtime.events import coletar_resposta
from aurora.runtime.events import serializar_eventos
from aurora.runtime.sessions import OrderedDatabaseSessionService
from aurora.runtime.sessions import adk_database_url
from aurora.runtime.sessions import tune_sqlite
from aurora.schemas import MensagemResponse
from aurora.storage.database import dispose_engine
from aurora.storage.database import get_engine
from aurora.storage.identity import criar_sessao_coordenada
from aurora.storage.identity import obter_identidade
from aurora.storage.seed import initialize_storage

logger = logging.getLogger(__name__)

RUN_TIMEOUT_SECONDS = 120

_RUN_CONFIG = RunConfig(
    streaming_mode=StreamingMode.NONE,
    max_llm_calls=20,
)


class AuroraRuntime:
    def __init__(self, session_service: OrderedDatabaseSessionService, runner: Runner):
        self.session_service = session_service
        self.runner = runner
        self._guard = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = {}

    @classmethod
    async def start(cls) -> AuroraRuntime:
        settings = get_settings()
        export_api_key(settings)
        initialize_storage(get_engine(), settings.dados_dir)
        session_service = OrderedDatabaseSessionService(
            adk_database_url(settings.adk_db_path)
        )
        tune_sqlite(session_service)
        await session_service.prime_timestamps()
        runner = Runner(
            app=build_app(),
            session_service=session_service,
            auto_create_session=False,
        )
        logger.info("Modelo configurado: %s", settings.gemini_model)
        logger.info("Diretório de dados: %s", settings.data_dir)
        return cls(session_service, runner)

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

    async def enviar_mensagem(self, session_id: str, texto: str) -> MensagemResponse:
        async with await self._lock(session_id):
            await self._exigir_adk(session_id)
            recebidos = []
            deadline = asyncio.timeout(RUN_TIMEOUT_SECONDS)
            try:
                async with deadline:
                    async with aclosing(
                        self.runner.run_async(
                            user_id=session_id,
                            session_id=session_id,
                            new_message=types.Content(
                                role="user",
                                parts=[types.Part(text=texto)],
                            ),
                            run_config=_RUN_CONFIG,
                        )
                    ) as eventos:
                        async for evento in eventos:
                            recebidos.append(evento)
            except TimeoutError:
                if not deadline.expired():
                    raise
                raise ExecucaoExpirada from None
            return MensagemResponse(
                resposta=coletar_resposta(recebidos),
                confirmacoes_pendentes=[],
            )

    async def listar_eventos(self, session_id: str) -> list[dict]:
        adk_session = await self._exigir_adk(session_id)
        return serializar_eventos(adk_session.events)

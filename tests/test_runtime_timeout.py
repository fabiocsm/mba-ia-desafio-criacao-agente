"""Regressões offline com Runner real e sessões SQLite temporárias."""

import asyncio
import tempfile
import unittest
from contextlib import suppress
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from aurora.api_routes.sessoes import router
from aurora.config import APP_NAME, Settings
from aurora.runtime.service import AuroraRuntime
from aurora.storage.database import dispose_engine


class StallingLlm(BaseLlm):
    stall: bool = True
    fail: bool = False
    _started: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)
    _closed: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)
    _cancelled: bool = PrivateAttr(default=False)

    async def generate_content_async(self, llm_request, stream=False):
        self._started.set()
        try:
            if self.fail:
                raise TimeoutError("Falha interna distinta do prazo do runtime")
            if self.stall:
                await asyncio.Event().wait()
            yield LlmResponse(
                content=types.Content(
                    role="model", parts=[types.Part(text="Atendimento retomado.")]
                )
            )
        except asyncio.CancelledError:
            self._cancelled = True
            raise
        finally:
            self._closed.set()


class RuntimeTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        dispose_engine()
        settings = Settings(
            _env_file=None, google_api_key="", aurora_data_dir=self.temp.name
        )
        self.model = StallingLlm(model="offline")
        app = App(
            name=APP_NAME,
            root_agent=LlmAgent(name="principal_teste", model=self.model, mode="chat"),
        )
        for target, value in (
            ("aurora.runtime.service.get_settings", settings),
            ("aurora.storage.database.get_settings", settings),
            ("aurora.runtime.service.build_app", app),
        ):
            mock = patch(target, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        # Um prazo curto deixa o teste determinístico sem chamar o provedor.
        deadline = patch(
            "aurora.runtime.service.RUN_TIMEOUT_SECONDS", 0.15, create=True
        )
        deadline.start()
        self.addCleanup(deadline.stop)
        self.runtime = await AuroraRuntime.start()
        self.session_id = await self.runtime.criar_sessao("101")

    async def asyncTearDown(self):
        await self.runtime.aclose()

    async def bounded(self, awaitable):
        task = asyncio.create_task(awaitable)
        done, _ = await asyncio.wait({task}, timeout=2)
        if not done:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            self.fail("Execução permaneceu bloqueada além do prazo do runtime")
        return task.result()

    async def test_timeout_cancels_runner_and_same_session_recovers_after_restart(self):
        with self.assertRaises(Exception) as raised:
            await self.bounded(
                self.runtime.enviar_mensagem(self.session_id, "Primeira mensagem")
            )
        self.assertEqual(type(raised.exception).__name__, "ExecucaoExpirada")
        self.assertTrue(self.model._started.is_set())
        self.assertTrue(self.model._closed.is_set())
        self.assertTrue(self.model._cancelled)
        before = await self.runtime.listar_eventos(self.session_id)
        self.assertTrue(before)
        self.assertEqual(before[0]["content"]["parts"][0]["text"], "Primeira mensagem")

        self.model.stall = False
        response = await self.bounded(
            self.runtime.enviar_mensagem(self.session_id, "Segunda mensagem")
        )
        self.assertEqual(response.resposta, "Atendimento retomado.")
        after = await self.runtime.listar_eventos(self.session_id)
        self.assertEqual(after[: len(before)], before)
        await self.runtime.aclose()
        self.runtime = await AuroraRuntime.start()
        self.assertEqual(await self.runtime.listar_eventos(self.session_id), after)
        response = await self.bounded(
            self.runtime.enviar_mensagem(self.session_id, "Após reinício")
        )
        self.assertEqual(response.resposta, "Atendimento retomado.")

    async def test_external_cancellation_propagates_and_releases_session(self):
        task = asyncio.create_task(
            self.runtime.enviar_mensagem(self.session_id, "Cancelar requisição")
        )
        await asyncio.wait_for(self.model._started.wait(), timeout=2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.model._closed.is_set())
        self.assertTrue(self.model._cancelled)
        self.model.stall = False
        response = await self.bounded(
            self.runtime.enviar_mensagem(self.session_id, "Nova requisição")
        )
        self.assertEqual(response.resposta, "Atendimento retomado.")

    async def test_unrelated_timeout_is_not_reclassified(self):
        self.model.fail = True
        with self.assertLogs(level="ERROR"), self.assertRaises(TimeoutError) as raised:
            await self.runtime.enviar_mensagem(self.session_id, "Erro interno")
        self.assertEqual(str(raised.exception), "Falha interna distinta do prazo do runtime")

    async def test_http_timeout_is_safe_json_and_missing_session_stays_404(self):
        app = FastAPI()
        app.include_router(router)
        app.state.runtime = self.runtime
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://teste"
        ) as client:
            missing = await client.post("/sessoes/ausente/mensagens", json={"texto": "Oi"})
            self.assertEqual(missing.status_code, 404)
            response = await self.bounded(
                client.post(
                    f"/sessoes/{self.session_id}/mensagens", json={"texto": "Oi"}
                )
            )
            self.assertEqual(response.status_code, 504)
            self.assertEqual(response.json(), {"detail": "Tempo limite de atendimento excedido."})
            self.assertEqual(response.headers["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()

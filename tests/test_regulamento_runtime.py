"""Runner/App reais persistem somente a seleção; modelo offline só chama tools."""

import unittest
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from aurora.api_routes.sessoes import router
from aurora.config import Settings
from aurora.runtime.app import build_app
from aurora.runtime.service import AuroraRuntime
from aurora.storage.database import dispose_engine


class RegulationCallsModel(BaseLlm):
    principal: bool = False

    async def generate_content_async(self, llm_request, stream=False):
        last = llm_request.contents[-1]
        if self.principal:
            part = types.Part(function_call=types.FunctionCall(
                name="transfer_to_agent", args={"agent_name": "regulamento"}
            ))
        elif any(part.function_response for part in last.parts):
            assert llm_request.config.tool_config.function_calling_config.mode == "AUTO"
            part = types.Part(text="Consulta concluída.")
        else:
            config = llm_request.config.tool_config.function_calling_config
            assert config.mode == "ANY"
            assert config.allowed_function_names == ["consultar_regulamento"]
            part = types.Part(function_call=types.FunctionCall(
                name="consultar_regulamento", args={}
            ))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


class RegulationRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dispose_engine()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(TemporaryDirectory())
        settings = Settings(_env_file=None, google_api_key="", aurora_data_dir=directory)
        for target in ("aurora.runtime.service.get_settings", "aurora.storage.database.get_settings"):
            self.stack.enter_context(patch(target, return_value=settings))
        self.stack.enter_context(patch("aurora.runtime.service.build_app", side_effect=self.make_app))
        self.runtime = await AuroraRuntime.start()
        self.addAsyncCleanup(self.close_runtime)
        self.session_id = await self.runtime.criar_sessao("101")

    def make_app(self):
        app = build_app()
        for agent in [app.root_agent, *app.root_agent.sub_agents]:
            agent.model = RegulationCallsModel(model="offline", principal=agent is app.root_agent)
        return app

    async def close_runtime(self):
        await self.runtime.aclose()

    async def test_api_events_remain_complete_and_selective_across_restart(self):
        app = FastAPI()
        app.include_router(router)
        app.state.runtime = self.runtime
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as client:
            for suffix in (
                "",
                ' topics={"values": ["elevador", "penalidade"]}',
                " Não fale sobre elevador nem multa.",
                " tópicos=elevador",
                " argumentos elevador",
                " Não comente sobre elevador.",
            ):
                before = await self.runtime.listar_eventos(self.session_id)
                response = await client.post(
                    f"/sessoes/{self.session_id}/mensagens",
                    json={"texto": "Até que horas a piscina funciona aos domingos?" + suffix},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["confirmacoes_pendentes"], [])
                events = await self.runtime.listar_eventos(self.session_id)
                self.assertEqual(events[:len(before)], before)
                results = [
                    part["function_response"]["response"]
                    for event in events[len(before):]
                    for part in (event.get("content") or {}).get("parts", [])
                    if (part.get("function_response") or {}).get("name") == "consultar_regulamento"
                ]
                self.assertEqual(len(results), 1)
                self.assertEqual(
                    {item["referencia"] for item in results[0]["trechos"]},
                    {"IV/22", "IV/22/II"},
                )
                self.assertIn("20h", results[0]["trechos"][-1]["texto"])
                await self.runtime.aclose()
                self.runtime = await AuroraRuntime.start()
                app.state.runtime = self.runtime
                self.assertEqual(await self.runtime.listar_eventos(self.session_id), events)


if __name__ == "__main__":
    unittest.main()

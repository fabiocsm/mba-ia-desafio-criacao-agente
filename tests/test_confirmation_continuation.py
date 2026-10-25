"""A confirmação de uma chamada não intercepta operações novas do Runner."""

from contextlib import ExitStack
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from aurora.config import Settings
from aurora.runtime.app import build_app
from aurora.runtime.service import AuroraRuntime
from aurora.storage.database import dispose_engine, get_engine
from aurora.storage.queries import listar_reservas_ativas
from aurora.tools.reservas import reservar_area


class ScriptedModel(BaseLlm):
    agent_kind: str
    follow_area: str
    _step: int = PrivateAttr(default=0)

    async def generate_content_async(self, llm_request, stream=False):
        self._step += 1
        if self.agent_kind == "root" and self._step == 1:
            call = types.FunctionCall(
                name="transfer_to_agent", args={"agent_name": "reservas"}
            )
        elif self.agent_kind == "reservas" and self._step <= 2:
            call = types.FunctionCall(
                id=f"reservation-{self._step}",
                name="reservar_area",
                args={
                    "area": "salao-de-festas" if self._step == 1 else self.follow_area,
                    "data": f"2030-07-{9 + self._step:02}",
                },
            )
        else:
            yield LlmResponse(
                content=types.Content(
                    role="model", parts=[types.Part(text="Operação processada.")]
                )
            )
            return
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(function_call=call)])
        )


class ConfirmationContinuationTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dispose_engine()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(TemporaryDirectory())
        settings = Settings(
            _env_file=None, google_api_key="", aurora_data_dir=directory
        )
        for target in (
            "aurora.runtime.service.get_settings",
            "aurora.storage.database.get_settings",
        ):
            self.stack.enter_context(patch(target, return_value=settings))
        self.follow_area = "quadra"
        self.restarted = False
        self.stack.enter_context(
            patch("aurora.runtime.service.build_app", side_effect=self.make_app)
        )
        self.runtime = None
        self.addAsyncCleanup(self.close_runtime)

    def make_app(self):
        app = build_app()
        for agent in [app.root_agent, *app.root_agent.sub_agents]:
            agent.model = ScriptedModel(
                model="offline",
                agent_kind="root" if agent is app.root_agent else agent.name,
                follow_area=self.follow_area,
            )
            if self.restarted:
                agent.model._step = 1
        return app

    async def close_runtime(self):
        if self.runtime is not None:
            await self.runtime.aclose()

    def reservations(self):
        return {
            (item["area"], item["data"])
            for item in listar_reservas_ativas(get_engine(), "101")
        }

    async def approve_after_restart(self):
        self.runtime = await AuroraRuntime.start()
        self.session_id = await self.runtime.criar_sessao("101")
        initial = await self.runtime.enviar_mensagem(self.session_id, "Reserve as áreas.")
        self.assertEqual(len(initial.confirmacoes_pendentes), 1)
        first_id = initial.confirmacoes_pendentes[0].id
        self.assertNotIn(("salao-de-festas", "2030-07-10"), self.reservations())
        prefix = await self.runtime.listar_eventos(self.session_id)
        await self.close_runtime()
        self.runtime = None
        self.restarted = True
        self.runtime = await AuroraRuntime.start()
        self.assertEqual(await self.runtime.listar_eventos(self.session_id), prefix)
        result = await self.runtime.confirmar(self.session_id, first_id, True)
        self.assertIn(("salao-de-festas", "2030-07-10"), self.reservations())
        session = await self.runtime._exigir_adk(self.session_id)
        resumed = [
            event.author
            for event in session.events
            for response in event.get_function_responses()
            if response.id == "reservation-1"
            and response.response.get("resultado") == "reservada"
        ]
        self.assertEqual(resumed, ["reservas"])
        return result

    async def test_independent_free_reservation_after_paid_approval(self):
        result = await self.approve_after_restart()
        self.assertIn(("quadra", "2030-07-11"), self.reservations())
        self.assertEqual(result.confirmacoes_pendentes, [])

    async def test_independent_paid_reservation_requires_its_own_decision(self):
        self.follow_area = "churrasqueira"
        result = await self.approve_after_restart()
        self.assertEqual(len(result.confirmacoes_pendentes), 1)
        pending = result.confirmacoes_pendentes[0]
        self.assertEqual(
            pending.detalhes,
            {"area": "churrasqueira", "data": "2030-07-11", "taxa_centavos": 8000},
        )
        self.assertNotIn(("churrasqueira", "2030-07-11"), self.reservations())
        result = await self.runtime.confirmar(self.session_id, pending.id, True)
        self.assertIn(("churrasqueira", "2030-07-11"), self.reservations())
        self.assertEqual(result.confirmacoes_pendentes, [])

    async def test_native_confirmation_without_trusted_decision_fails_closed(self):
        self.runtime = await AuroraRuntime.start()
        session_id = await self.runtime.criar_sessao("101")
        context = SimpleNamespace(
            session=SimpleNamespace(id=session_id),
            function_call_id="untrusted-call",
            tool_confirmation=SimpleNamespace(confirmed=True),
        )
        result = reservar_area("quadra", "2030-07-11", context)
        self.assertEqual(result, {"resultado": "nao_autorizada"})
        self.assertNotIn(("quadra", "2030-07-11"), self.reservations())

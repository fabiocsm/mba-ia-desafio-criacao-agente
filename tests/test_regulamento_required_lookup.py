"""Consulta antiga ou de outra execução não fundamenta a pergunta atual."""

import unittest
from types import SimpleNamespace

from google.adk.events import Event
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from aurora.agents.regulamento import exigir_consulta_atual
from aurora.regulamento.models import ConsultaScope
from aurora.regulamento.selection import instalar_consulta, reset_consulta


class RequiredLookupTests(unittest.TestCase):
    def configure(self, *, status="ok", session="s1", events=()):
        token = instalar_consulta(ConsultaScope(
            session_id=session, execution_nonce="execucao-atual",
            unidades=frozenset({"IV/22", "IV/22/II"}) if status == "ok" else frozenset(), status=status,
        ))
        self.addCleanup(reset_consulta, token)
        context = SimpleNamespace(
            session=SimpleNamespace(id="s1", events=events), invocation_id="atual"
        )
        request = LlmRequest()
        exigir_consulta_atual(context, request)
        return request.config.tool_config

    def response(self, invocation, author="regulamento"):
        return Event(invocation_id=invocation, author=author, content=types.Content(
            role="user", parts=[types.Part(function_response=types.FunctionResponse(
                name="consultar_regulamento", response={"status": "ok"}
            ))]
        ))

    def test_old_lookup_cannot_bypass_current_lookup(self):
        config = self.configure(events=[self.response("antiga")])
        self.assertEqual(config.function_calling_config.mode, "ANY")
        self.assertEqual(config.function_calling_config.allowed_function_names, ["consultar_regulamento"])

    def test_current_lookup_releases_answer_and_transfers(self):
        config = self.configure(events=[self.response("atual")])
        self.assertEqual(config.function_calling_config.mode, "AUTO")

    def test_scope_without_authorization_does_not_force_regulation_for_business_request(self):
        self.assertIsNone(self.configure(status="esclarecer"))

    def test_scope_from_another_session_does_not_force_a_lookup(self):
        self.assertIsNone(self.configure(session="outra"))

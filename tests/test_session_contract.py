"""A ausência da sessão prevalece sobre erros do corpo em todas as rotas."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from aurora.api_routes.confirmacoes import router as confirmacoes
from aurora.api_routes.sessoes import router as sessoes
from aurora.errors import ConfirmacaoConflito
from aurora.errors import SessaoInexistente


class SessionContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.app.include_router(sessoes)
        self.app.include_router(confirmacoes)
        self.runtime = SimpleNamespace(
            _exigir_adk=AsyncMock(),
            enviar_mensagem=AsyncMock(),
            confirmar=AsyncMock(),
            listar_eventos=AsyncMock(),
        )
        self.app.state.runtime = self.runtime
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://teste"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_missing_session_is_404_even_with_invalid_or_missing_json(self):
        self.runtime._exigir_adk.side_effect = SessaoInexistente
        for endpoint in ("mensagens", "confirmacoes"):
            for body in (b"", b"{", b"[]", b"{}", b"null", b'"texto"', b"\xff"):
                with self.subTest(endpoint=endpoint, body=body):
                    response = await self.client.post(
                        f"/sessoes/ausente/{endpoint}", content=body,
                        headers={"content-type": "application/json"},
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.json(), {"detail": "Sessão não encontrada"})
        response = await self.client.get("/sessoes/ausente/eventos")
        self.assertEqual(response.status_code, 404)
        self.runtime.enviar_mensagem.assert_not_awaited()
        self.runtime.confirmar.assert_not_awaited()
        self.runtime.listar_eventos.assert_not_awaited()

    async def test_existing_session_rejects_invalid_confirmation_without_execution(self):
        for payload in (
            {}, {"id": "x", "confirmado": "true"},
            {"id": "x", "confirmado": 1},
            {"id": "x", "confirmado": True, "apartamento": "302"},
            {"id": "x", "confirmado": True, "data": "2030-01-01"},
        ):
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/sessoes/existente/confirmacoes", json=payload
                )
                self.assertEqual(response.status_code, 422)
        self.runtime.confirmar.assert_not_awaited()

    async def test_unknown_or_empty_confirmation_id_is_409(self):
        self.runtime.confirmar.side_effect = ConfirmacaoConflito
        for proposal_id in ("id-inexistente", ""):
            with self.subTest(proposal_id=proposal_id):
                response = await self.client.post(
                    "/sessoes/existente/confirmacoes",
                    json={"id": proposal_id, "confirmado": True},
                )
                self.assertEqual(response.status_code, 409)
                self.runtime.confirmar.assert_awaited_with("existente", proposal_id, True)

    async def test_confirmation_schema_and_boolean_decision_remain_in_contract(self):
        self.runtime.confirmar.return_value = {
            "resposta": "", "confirmacoes_pendentes": []
        }
        for decision in (True, False):
            response = await self.client.post(
                "/sessoes/existente/confirmacoes",
                json={"id": "pendente", "confirmado": decision},
            )
            self.assertEqual(response.status_code, 200)
            self.runtime.confirmar.assert_awaited_with("existente", "pendente", decision)
        operation = self.app.openapi()["paths"]["/sessoes/{session_id}/confirmacoes"]["post"]
        self.assertIn("application/json", operation["requestBody"]["content"])

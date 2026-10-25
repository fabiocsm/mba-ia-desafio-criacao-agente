"""Exercita Gemini/SDK reais com respostas HTTP locais, sem chave ou rede."""

import unittest
from unittest.mock import patch

import httpx
from google import genai
from google.adk.models.llm_request import LlmRequest
from google.genai import errors, types

from aurora.agents.model import build_model


class ModelRetryTests(unittest.IsolatedAsyncioTestCase):
    async def generate(self, statuses):
        self.calls = []
        real_client = genai.Client

        def respond(request):
            self.calls.append(request.content)
            status = statuses[min(len(self.calls) - 1, len(statuses) - 1)]
            if status != 200:
                return httpx.Response(status, json={"error": {"code": status, "message": "offline"}})
            return httpx.Response(200, json={"candidates": [{
                "content": {"role": "model", "parts": [{"text": "Concluído."}]},
                "finishReason": "STOP",
            }]})

        def make_client(**kwargs):
            kwargs["api_key"] = "offline"
            options = kwargs["http_options"]
            # Só elimina a espera do teste; tentativas e status vêm da produção.
            options.retry_options.initial_delay = 0
            options.retry_options.max_delay = 0
            options.retry_options.jitter = 0
            options.async_client_args = {"transport": httpx.MockTransport(respond)}
            return real_client(**kwargs)

        model = build_model()
        with patch("google.genai.Client", side_effect=make_client):
            client = model.api_client
        try:
            request = LlmRequest(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part(text="Olá")])],
            )
            return [response async for response in model.generate_content_async(request)]
        finally:
            await client.aio.aclose()
            client.close()

    async def test_transient_503_retries_the_same_request_then_succeeds(self):
        results = await self.generate([503, 200])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0], self.calls[1])
        self.assertEqual(results[0].content.parts[0].text, "Concluído.")

    async def test_permanent_403_is_not_retried(self):
        with self.assertRaises(errors.ClientError):
            await self.generate([403])
        self.assertEqual(len(self.calls), 1)

    async def test_repeated_503_has_a_finite_attempt_limit(self):
        with self.assertRaises(errors.ServerError):
            await self.generate([503])
        self.assertEqual(len(self.calls), 4)

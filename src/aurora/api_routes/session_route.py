"""Verifica a sessão antes de ler ou validar o corpo HTTP."""

from fastapi import HTTPException, Request
from fastapi.routing import APIRoute

from aurora.errors import SessaoInexistente


class SessionRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def exigir_sessao(request: Request):
            session_id = request.path_params.get("session_id")
            if session_id is not None:
                try:
                    await request.app.state.runtime._exigir_adk(session_id)
                except SessaoInexistente:
                    raise HTTPException(
                        status_code=404, detail="Sessão não encontrada"
                    ) from None
            return await handler(request)

        return exigir_sessao

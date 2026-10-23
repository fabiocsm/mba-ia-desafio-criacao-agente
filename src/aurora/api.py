"""API HTTP do Residencial Aurora."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from aurora.api_routes.confirmacoes import router as confirmacoes_router
from aurora.api_routes.sessoes import router as sessoes_router
from aurora.api_routes.verificacao import router as verificacao_router
from aurora.runtime.service import AuroraRuntime

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = await AuroraRuntime.start()
    try:
        yield
    finally:
        await app.state.runtime.aclose()


app = FastAPI(title="Residencial Aurora", lifespan=lifespan)
app.include_router(sessoes_router)
app.include_router(confirmacoes_router)
app.include_router(verificacao_router)


@app.exception_handler(Exception)
async def falha_nao_tratada(request: Request, exc: Exception) -> JSONResponse:
    """Resposta JSON fixa. O corpo não repete a exceção, a chave nem dados de moradores."""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    logger.error("Falha interna em %s (%s)", request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Falha interna."})

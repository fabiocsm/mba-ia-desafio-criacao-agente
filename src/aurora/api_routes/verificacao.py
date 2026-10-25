"""Leituras diretas do avaliador. Não passam pelo modelo nem são ferramentas."""

from __future__ import annotations

from fastapi import APIRouter

from aurora.schemas import ReservaOut
from aurora.schemas import VisitanteOut
from aurora.storage.database import get_engine
from aurora.storage.queries import listar_reservas_ativas
from aurora.storage.queries import listar_visitantes

router = APIRouter()


@router.get(
    "/apartamentos/{apartamento}/reservas",
    response_model=list[ReservaOut],
)
def reservas_do_apartamento(apartamento: str) -> list[ReservaOut]:
    return [
        ReservaOut.model_validate(item)
        for item in listar_reservas_ativas(get_engine(), apartamento)
    ]


@router.get(
    "/apartamentos/{apartamento}/visitantes",
    response_model=list[VisitanteOut],
)
def visitantes_do_apartamento(apartamento: str) -> list[VisitanteOut]:
    return [
        VisitanteOut.model_validate(item)
        for item in listar_visitantes(get_engine(), apartamento)
    ]

"""Subida da API e restauração explícita.

`serve` segura o lock compartilhado o tempo todo e não restaura.
`restaurar` exige o lock exclusivo, com a API parada, e só termina depois
de conferir os dois bancos.
"""

from __future__ import annotations

import sys

import uvicorn

from aurora.config import get_settings
from aurora.storage.maintenance import LOCK_NAME
from aurora.storage.maintenance import LockOcupado
from aurora.storage.maintenance import OperationLock
from aurora.storage.maintenance import marker_present
from aurora.storage.reset import RestauracaoErro
from aurora.storage.reset import executar_restauracao


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["serve"]:
        _serve()
        return
    if args == ["restaurar"]:
        _restaurar()
        return
    print("Uso: aurora serve | aurora restaurar", file=sys.stderr)
    raise SystemExit(2)


def _serve() -> None:
    settings = get_settings()
    lock = OperationLock(settings.data_dir / LOCK_NAME)
    try:
        lock.acquire_shared()
    except LockOcupado:
        print(
            "Não foi possível iniciar: a restauração detém o acesso exclusivo.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    if marker_present(settings.data_dir):
        lock.release()
        print(
            "Restauração incompleta. A API não foi iniciada. "
            "Com todos os processos parados, execute: uv run aurora restaurar",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        uvicorn.run(
            "aurora.api:app",
            host="0.0.0.0",
            port=8000,
            workers=1,
            reload=False,
        )
    finally:
        lock.release()


def _restaurar() -> None:
    try:
        executar_restauracao(get_settings())
    except RestauracaoErro as exc:
        print(exc.mensagem, file=sys.stderr)
        raise SystemExit(1) from None
    print(
        "Restauração concluída. Reservas e visitantes voltaram ao estado "
        "inicial. Sessões, eventos, pendências e decisões foram apagados. "
        "O ledger de códigos foi preservado."
    )


if __name__ == "__main__":
    main()

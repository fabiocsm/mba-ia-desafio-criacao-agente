"""Subida da API com um worker, sem reload."""

from __future__ import annotations

import sys

import uvicorn


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["serve"]:
        print("Uso: aurora serve", file=sys.stderr)
        raise SystemExit(2)
    uvicorn.run(
        "aurora.api:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        reload=False,
    )


if __name__ == "__main__":
    main()

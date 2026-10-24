"""Lock de operação e marcador de restauração.

O mesmo arquivo absoluto é compartilhado pelo serviço e pela restauração.
Ele não é removido. Nenhuma conexão de banco abre antes do lock.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
from pathlib import Path

LOCK_NAME = "operation.lock"
MARKER_NAME = "reset-in-progress.json"
_MARKER_PAYLOAD = {"versao": 1, "operacao": "restaurar"}


class LockOcupado(Exception):
    """Outro processo detém o lock em modo incompatível."""


class OperationLock:
    """flock não bloqueante. O descritor permanece aberto enquanto o lock vale."""

    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self._fd: int | None = None

    def acquire_shared(self) -> None:
        self._acquire(fcntl.LOCK_SH)

    def acquire_exclusive(self) -> None:
        self._acquire(fcntl.LOCK_EX)

    def _acquire(self, mode: int) -> None:
        if self._fd is not None:
            raise RuntimeError("Lock de operação já adquirido.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, mode | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if isinstance(exc, BlockingIOError) or exc.errno in (
                errno.EAGAIN,
                errno.EACCES,
            ):
                raise LockOcupado() from None
            raise
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

    @property
    def held(self) -> bool:
        return self._fd is not None


def marker_path(data_dir: Path) -> Path:
    return data_dir.expanduser().resolve() / MARKER_NAME


def marker_present(data_dir: Path) -> bool:
    return marker_path(data_dir).is_file()


def write_marker(data_dir: Path) -> Path:
    """Grava o marcador e sincroniza arquivo e diretório antes de qualquer banco."""
    directory = data_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / MARKER_NAME
    payload = json.dumps(_MARKER_PAYLOAD, ensure_ascii=False, separators=(",", ":"))
    payload = payload + "\n"
    fd = os.open(target, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(directory)
    return target


def remove_marker(data_dir: Path) -> None:
    """Remove o marcador só depois das duas bases verificadas."""
    directory = data_dir.expanduser().resolve()
    target = directory / MARKER_NAME
    os.remove(target)
    _fsync_dir(directory)


def _fsync_dir(directory: Path) -> None:
    dir_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)

"""O ciclo de vida real do runtime impede reset concorrente, sem chamar Gemini."""

import asyncio
import os
import sqlite3
import sys
import unittest
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from unittest.mock import patch

from aurora.config import Settings
from aurora.runtime.service import AuroraRuntime
from aurora.storage.database import dispose_engine
from aurora.storage.maintenance import LOCK_NAME, LockOcupado, OperationLock, write_marker


class RuntimeMaintenanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dispose_engine()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(TemporaryDirectory())
        self.settings = Settings(
            _env_file=None, google_api_key="", aurora_data_dir=directory
        )
        for target in (
            "aurora.runtime.service.get_settings",
            "aurora.storage.database.get_settings",
        ):
            self.stack.enter_context(patch(target, return_value=self.settings))
        self.runtime = None
        self.addAsyncCleanup(self.close_runtime)
        self.addCleanup(dispose_engine)

    async def close_runtime(self):
        if self.runtime is not None:
            runtime, self.runtime = self.runtime, None
            await runtime.aclose()

    async def restore(self):
        environment = dict(os.environ)
        environment.update(AURORA_DATA_DIR=self.settings.aurora_data_dir, GOOGLE_API_KEY="")
        environment.pop("AURORA_RESET_INTERRUPT", None)
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "aurora.cli",
            "restaurar",
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        except BaseException:
            process.kill()
            await process.wait()
            raise
        return process.returncode, stdout.decode(), stderr.decode()

    def assert_exclusive_available(self):
        lock = OperationLock(self.settings.data_dir / LOCK_NAME)
        lock.acquire_exclusive()
        lock.release()

    async def test_restore_refuses_live_runtime_and_succeeds_after_close(self):
        self.runtime = await AuroraRuntime.start()
        session_id = await self.runtime.criar_sessao("101")
        before = await self.runtime.listar_eventos(session_id)
        status, stdout, stderr = await self.restore()
        self.assertNotEqual(status, 0, stdout + stderr)
        self.assertIn("API está em execução", stderr)
        self.assertEqual(await self.runtime.listar_eventos(session_id), before)
        self.assertFalse((self.settings.data_dir / "reset-in-progress.json").exists())
        with sqlite3.connect(self.settings.business_db_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM session_identity").fetchone(), (1,))
        await self.close_runtime()
        status, stdout, stderr = await self.restore()
        self.assertEqual(status, 0, stdout + stderr)
        with sqlite3.connect(self.settings.business_db_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM session_identity").fetchone(), (0,))

    async def test_marker_refuses_start_before_opening_databases_and_releases_lock(self):
        write_marker(self.settings.data_dir)
        with patch("aurora.runtime.service.get_engine") as engine:
            with self.assertRaisesRegex(RuntimeError, "Restauração incompleta"):
                await AuroraRuntime.start()
        engine.assert_not_called()
        self.assertFalse(self.settings.business_db_path.exists())
        self.assertFalse(self.settings.adk_db_path.exists())
        self.assert_exclusive_available()

    async def test_exclusive_restore_lock_refuses_start_before_opening_databases(self):
        lock = OperationLock(self.settings.data_dir / LOCK_NAME)
        lock.acquire_exclusive()
        try:
            with patch("aurora.runtime.service.get_engine") as engine:
                with self.assertRaises(LockOcupado):
                    self.runtime = await AuroraRuntime.start()
            engine.assert_not_called()
            self.assertFalse(self.settings.business_db_path.exists())
            self.assertFalse(self.settings.adk_db_path.exists())
        finally:
            lock.release()

    async def test_failed_start_closes_databases_and_releases_lock(self):
        with patch("aurora.runtime.service.build_app", side_effect=RuntimeError("startup")):
            with self.assertRaisesRegex(RuntimeError, "startup"):
                await AuroraRuntime.start()
        self.assert_exclusive_available()
        status, stdout, stderr = await self.restore()
        self.assertEqual(status, 0, stdout + stderr)

    async def test_cancelled_start_releases_lock(self):
        started = asyncio.Event()

        async def wait_for_cancellation(_runtime):
            started.set()
            await asyncio.Event().wait()

        with patch.object(AuroraRuntime, "reconciliar_metadados", wait_for_cancellation):
            task = asyncio.create_task(AuroraRuntime.start())
            await asyncio.wait_for(started.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assert_exclusive_available()
        status, stdout, stderr = await self.restore()
        self.assertEqual(status, 0, stdout + stderr)

    async def test_failed_close_still_releases_lock(self):
        self.runtime = await AuroraRuntime.start()
        close = self.runtime.session_service.close

        async def close_then_fail():
            await close()
            raise RuntimeError("close")

        with patch.object(self.runtime.session_service, "close", side_effect=close_then_fail):
            with self.assertRaisesRegex(RuntimeError, "close"):
                await self.close_runtime()
        self.assert_exclusive_available()
        status, stdout, stderr = await self.restore()
        self.assertEqual(status, 0, stdout + stderr)


if __name__ == "__main__":
    unittest.main()

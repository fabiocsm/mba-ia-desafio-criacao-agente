"""O probe operacional não deixa uma chamada de rede sem prazo."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class CheckModelTimeoutTests(unittest.TestCase):
    def test_probe_configures_finite_http_timeout(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "check_model.py"
        spec = importlib.util.spec_from_file_location("check_model", path)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        settings = SimpleNamespace(google_api_key="test-key", gemini_model="offline")
        client = MagicMock()
        with (
            patch.object(probe, "get_settings", return_value=settings),
            patch.object(probe, "export_api_key"),
            patch.object(probe.genai, "Client", return_value=client) as factory,
            patch.object(probe, "_chamou_ping", return_value=True),
            patch("builtins.print"),
        ):
            self.assertEqual(probe.main(), 0)
        options = factory.call_args.kwargs.get("http_options")
        self.assertIsNotNone(options, "Probe deve definir HttpOptions com prazo finito")
        self.assertGreater(options.timeout, 0)
        self.assertLessEqual(options.timeout, 120_000)


if __name__ == "__main__":
    unittest.main()

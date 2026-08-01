from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.local_supervisor import supervisor


class FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class RunLocalTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)

        reports_directory = Path(self._temp_dir.name) / "reports" / "local_supervisor"
        history_directory = reports_directory / "history"
        last_call_path = reports_directory / "last_call.json"

        patcher_reports = patch.object(
            supervisor, "REPORTS_DIRECTORY", reports_directory
        )
        patcher_history = patch.object(
            supervisor, "HISTORY_DIRECTORY", history_directory
        )
        patcher_last_call = patch.object(
            supervisor, "LAST_CALL_PATH", last_call_path
        )
        patcher_reports.start()
        patcher_history.start()
        patcher_last_call.start()
        self.addCleanup(patcher_reports.stop)
        self.addCleanup(patcher_history.stop)
        self.addCleanup(patcher_last_call.stop)

        self.history_directory = history_directory
        self.last_call_path = last_call_path

    def test_rejects_model_not_in_allowlist_without_network_call(self) -> None:
        with patch.object(supervisor.urllib.request, "urlopen") as urlopen_mock:
            with self.assertRaises(supervisor.LocalSupervisorError):
                supervisor.run_local_task(
                    prompt="hello",
                    model="some-other-model:99b",
                )
        urlopen_mock.assert_not_called()

    def test_builds_expected_request_and_parses_response(self) -> None:
        response_payload = {
            "model": "qwen2.5-coder:7b",
            "response": "print('hello')",
            "done": True,
            "total_duration": 123456,
            "eval_count": 7,
            "eval_duration": 654321,
        }
        fake_response = FakeHttpResponse(
            json.dumps(response_payload).encode("utf-8")
        )

        with patch.object(
            supervisor.urllib.request,
            "urlopen",
            return_value=fake_response,
        ) as urlopen_mock:
            result = supervisor.run_local_task(
                prompt="write a hello world function",
                timeout=5.0,
            )

        self.assertEqual(urlopen_mock.call_count, 1)
        (request,), kwargs = urlopen_mock.call_args
        self.assertEqual(request.full_url, supervisor.OLLAMA_GENERATE_URL)
        self.assertEqual(kwargs["timeout"], 5.0)

        sent_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent_body["model"], "qwen2.5-coder:7b")
        self.assertEqual(
            sent_body["prompt"], "write a hello world function"
        )
        self.assertIs(sent_body["stream"], False)

        self.assertEqual(result.model, "qwen2.5-coder:7b")
        self.assertEqual(result.response, "print('hello')")
        self.assertEqual(result.total_duration_ns, 123456)
        self.assertEqual(result.eval_count, 7)

    def test_writes_last_call_and_history_evidence(self) -> None:
        response_payload = {
            "response": "OK",
            "done": True,
            "total_duration": 10,
            "eval_count": 1,
            "eval_duration": 5,
        }
        fake_response = FakeHttpResponse(
            json.dumps(response_payload).encode("utf-8")
        )

        with patch.object(
            supervisor.urllib.request,
            "urlopen",
            return_value=fake_response,
        ):
            result = supervisor.run_local_task(prompt="ping")

        self.assertTrue(self.last_call_path.is_file())
        history_files = list(self.history_directory.glob("call_*.json"))
        self.assertEqual(len(history_files), 1)
        self.assertEqual(result.history_path, history_files[0])
        self.assertEqual(result.last_call_path, self.last_call_path)

        last_call_record = json.loads(
            self.last_call_path.read_text(encoding="utf-8")
        )
        self.assertEqual(last_call_record["model"], "qwen2.5-coder:7b")
        self.assertEqual(last_call_record["prompt"], "ping")
        self.assertEqual(last_call_record["response"], "OK")
        self.assertEqual(
            last_call_record["response_sha256"], result.response_sha256
        )

    def test_maps_url_error_to_local_supervisor_error(self) -> None:
        with patch.object(
            supervisor.urllib.request,
            "urlopen",
            side_effect=supervisor.urllib.error.URLError("connection refused"),
        ):
            with self.assertRaises(supervisor.LocalSupervisorError):
                supervisor.run_local_task(prompt="hello")

    def test_maps_http_error_to_local_supervisor_error(self) -> None:
        http_error = supervisor.urllib.error.HTTPError(
            url=supervisor.OLLAMA_GENERATE_URL,
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

        with patch.object(
            supervisor.urllib.request,
            "urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(supervisor.LocalSupervisorError):
                supervisor.run_local_task(prompt="hello")


if __name__ == "__main__":
    unittest.main()

import http.client
import io
import json
import math
import os
import shlex
import struct
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from cms.datavis.tests.chart_exporter_mock import (
    CONTROL_PREFIX,
    ERRORS,
    INFRA_ERRORS,
    MALFORMED,
    MAX_BODY_BYTES,
    PNG,
    PNG_HEIGHT,
    PNG_WIDTH,
    SCENARIOS,
    Behaviour,
    ChartExporterMock,
    mock_from_args,
    parse_args,
)

TIMEOUT = 5
VALID_REQUEST = {"language": "en", "device": "desktop", "chart_config": {"chart": {"type": "line"}, "series": []}}
JSON_HEADERS = {"Content-Type": "application/json"}
RESPONSE_FIELDS = ["id", "created_at", "bucket", "key", "content_type", "size_bytes", "width", "height"]
GENERATED_REQUEST_ID = r"\A[0-9a-f]{32}\Z"
CLI_DEFAULTS = {
    "host": "127.0.0.1",
    "port": 30300,
    "scenario": "success",
    "delay": None,
    "bucket": "ons-charts",
    "key_prefix": "charts/",
    "output_dir": None,
    "max_concurrent": None,
    "queue_timeout": 5.0,
    "quiet": False,
    "behaviour": Behaviour("success"),
}
CLI_OPTIONS = {
    "host": "localhost",
    "port": 8000,
    "scenario": "hang",
    "delay": 0.5,
    "bucket": "my-bucket",
    "key_prefix": "exports/",
    "output_dir": "media",
    "max_concurrent": 2,
    "queue_timeout": 1.5,
    "quiet": True,
    "behaviour": Behaviour("hang", 0.5),
}


def send(
    mock: ChartExporterMock, method: str = "POST", path: str = "/charts", *, timeout: float = TIMEOUT, **kwargs: Any
) -> requests.Response:
    return requests.request(method, f"{mock.url}{path}", timeout=timeout, **kwargs)


def render(
    mock: ChartExporterMock, *, headers: dict[str, str] | None = None, timeout: float = TIMEOUT
) -> requests.Response:
    """Send a valid render request."""
    return send(mock, json=VALID_REQUEST, headers=headers, timeout=timeout)


def post_json(mock: ChartExporterMock, payload: Any) -> requests.Response:
    return send(mock, data=json.dumps(payload), headers=JSON_HEADERS)


def without(field: str) -> dict[str, Any]:
    return {name: value for name, value in VALID_REQUEST.items() if name != field}


class ChartExporterMockTestCase(SimpleTestCase):
    mock: ChartExporterMock

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock = cls.enterClassContext(ChartExporterMock())

    def setUp(self):
        self.mock.reset()

    def assert_errors(self, response: requests.Response, status: int, *codes: str) -> None:
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(
            response.json(), {"errors": [{"code": code, "description": ERRORS[code][1]} for code in codes]}
        )

    def wait_until(self, condition: Callable[[], bool]) -> None:
        deadline = time.monotonic() + TIMEOUT
        while not condition():
            if time.monotonic() > deadline:
                self.fail("Timed out waiting for the mock")
            time.sleep(0.01)

    def render_in_background(self, mock: ChartExporterMock) -> Future[requests.Response]:
        """Render from another thread. On cleanup, reset() releases the request if it's still waiting."""
        pool = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(pool.shutdown)
        self.addCleanup(mock.reset)
        return pool.submit(render, mock)


class ChartExporterMockContractTests(ChartExporterMockTestCase):
    def test_success(self):
        response = render(self.mock)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        body = response.json()
        self.assertEqual(list(body), RESPONSE_FIELDS)
        self.assertEqual(uuid.UUID(body["id"]).version, 4)
        self.assertTrue(body["created_at"].endswith("Z"))
        self.assertEqual(datetime.fromisoformat(body["created_at"]).utcoffset(), timedelta(0))
        self.assertEqual(body["bucket"], "ons-charts")
        self.assertEqual(body["key"], f"charts/{body['id']}.png")
        self.assertEqual(body["content_type"], "image/png")
        self.assertEqual(body["size_bytes"], len(PNG))
        self.assertEqual((body["width"], body["height"]), (1200, 640))
        self.assertEqual((body["width"], body["height"]), struct.unpack(">II", PNG[16:24]))

    def test_placeholder_png(self):
        self.assertEqual(PNG[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(PNG[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", PNG[16:24]), (PNG_WIDTH, PNG_HEIGHT))

    def test_bucket_and_key_prefix(self):
        for key_prefix, expected in [("exports/", "exports/"), ("exports", "exports/"), ("a/b", "a/b/"), ("", "")]:
            with (
                self.subTest(key_prefix=key_prefix),
                ChartExporterMock(bucket="my-bucket", key_prefix=key_prefix) as mock,
            ):
                body = render(mock).json()
                self.assertEqual(body["bucket"], "my-bucket")
                self.assertEqual(body["key"], f"{expected}{body['id']}.png")

    def test_output_dir(self):
        with TemporaryDirectory() as output_dir, ChartExporterMock(output_dir=output_dir) as mock:
            key = render(mock).json()["key"]
            self.assertEqual((Path(output_dir) / key).read_bytes(), PNG)

            not_written = [*MALFORMED, "render_failed", "renderer_busy", "bad_gateway"]
            mock.queue(*not_written)
            for _ in not_written:
                render(mock)
            post_json(mock, {})

            written = [
                path.relative_to(output_dir).as_posix() for path in Path(output_dir).rglob("*") if path.is_file()
            ]
            self.assertEqual(written, [key])

    def test_validation(self):
        language, device, config, body = (
            "invalid_language",
            "invalid_device",
            "invalid_chart_config",
            "invalid_request_body",
        )
        cases = [
            ({}, [language, device, config]),
            (None, [body]),
            ([1], [body]),
            ("x", [body]),
            (1, [body]),
            (without("language"), [language]),
            (without("device"), [device]),
            (without("chart_config"), [config]),
            ({**VALID_REQUEST, "language": "cy"}, [language]),
            ({**VALID_REQUEST, "language": None}, [language]),
            ({**VALID_REQUEST, "device": "mobile"}, [device]),
            ({**VALID_REQUEST, "device": None}, [device]),
            ({**VALID_REQUEST, "chart_config": {}}, [config]),
            ({**VALID_REQUEST, "chart_config": []}, [config]),
            ({**VALID_REQUEST, "chart_config": [{"a": 1}]}, [config]),
            ({**VALID_REQUEST, "chart_config": None}, [config]),
            ({**VALID_REQUEST, "chart_config": "x"}, [config]),
            ({**VALID_REQUEST, "extra": 1}, [body]),
            ({**VALID_REQUEST, "extra": 1, "more": 2}, [body]),
            ({"zzz": 1, "language": 1, "device": None, "chart_config": "x"}, [language, device, config, body]),
        ]
        for payload, codes in cases:
            with self.subTest(payload=payload):
                self.assert_errors(post_json(self.mock, payload), 400, *codes)

    def test_unparseable_body(self):
        for data in [b"", b'{"language": ', b"\xff\xfe"]:
            with self.subTest(data=data):
                self.assert_errors(send(self.mock, data=data, headers=JSON_HEADERS), 400, "invalid_request_body")

    def test_body_that_is_not_utf8(self):
        response = send(self.mock, data=b'{"a": "\x80"}', headers=JSON_HEADERS)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"errors": [{"code": "http_error", "description": "There was an error parsing the body"}]}
        )

    def test_unsupported_media_type(self):
        for content_type in [None, "text/plain", "application/xml", "application/vnd.api+json", "multipart/form-data"]:
            with self.subTest(content_type=content_type):
                headers = {"Content-Type": content_type} if content_type else {}
                response = send(self.mock, data=json.dumps(VALID_REQUEST), headers=headers)
                self.assert_errors(response, 415, "unsupported_media_type")

    def test_json_suffix_media_type_is_parsed_before_it_is_rejected(self):
        response = send(self.mock, data=b"{", headers={"Content-Type": "application/vnd.api+json"})
        self.assert_errors(response, 400, "invalid_request_body")

        response = send(self.mock, data=b"{", headers={"Content-Type": "text/plain"})
        self.assert_errors(response, 415, "unsupported_media_type")

    def test_media_type_is_case_insensitive_and_ignores_parameters(self):
        headers = {"Content-Type": "Application/JSON; charset=utf-8"}
        self.assertEqual(send(self.mock, data=json.dumps(VALID_REQUEST), headers=headers).status_code, 201)

    def test_body_too_large(self):
        for path in ["/charts", "/nope"]:
            with self.subTest(path=path):
                response = send(self.mock, path=path, data=b" " * (MAX_BODY_BYTES + 1), headers=JSON_HEADERS)
                self.assert_errors(response, 413, "request_body_too_large")
                self.assertEqual(
                    response.json()["errors"][0]["description"], "Request body must not exceed 1048576 bytes."
                )

    def test_body_too_large_is_rejected_before_it_is_read(self):
        host, port = self.mock.url.removeprefix("http://").split(":")
        connection = http.client.HTTPConnection(host, int(port), timeout=TIMEOUT)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/charts")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
        connection.endheaders()  # no body follows

        response = connection.getresponse()

        self.assertEqual(response.status, 413)
        self.assertEqual(json.loads(response.read())["errors"][0]["code"], "request_body_too_large")
        self.assertIsNone(self.mock.requests[0].body)

    def test_body_at_size_limit(self):
        data = json.dumps(VALID_REQUEST).encode().ljust(MAX_BODY_BYTES)
        self.assertEqual(len(data), MAX_BODY_BYTES)

        self.assertEqual(send(self.mock, data=data, headers=JSON_HEADERS).status_code, 201)

    def test_double_slash_is_routed_as_sent(self):
        response = send(self.mock, path="//charts", json=VALID_REQUEST)

        self.assert_errors(response, 404, "not_found")
        self.assertEqual(self.mock.requests[-1].path, "//charts")

    def test_unknown_path(self):
        for method, path in [("POST", "/nope"), ("GET", "/"), ("POST", "/charts/123")]:
            with self.subTest(method=method, path=path):
                self.assert_errors(send(self.mock, method, path, json=VALID_REQUEST), 404, "not_found")

    def test_method_not_allowed(self):
        cases = [
            *((method, "/charts", "POST") for method in ["GET", "PUT", "PATCH", "DELETE", "OPTIONS"]),
            ("POST", "/health", "GET"),
            ("DELETE", "/health", "GET"),
        ]
        for method, path, allow in cases:
            with self.subTest(method=method, path=path):
                response = send(self.mock, method, path)
                self.assert_errors(response, 405, "method_not_allowed")
                self.assertEqual(response.headers["Allow"], allow)

    def test_head_gets_no_body(self):
        response = send(self.mock, "HEAD", "/charts")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers["Allow"], "POST")
        self.assertEqual(response.content, b"")

    def test_request_id_is_echoed(self):
        for request_id in ["abc-123", "A.b:c_D-9", "x" * 128]:
            with self.subTest(request_id=request_id):
                response = render(self.mock, headers={"X-Request-Id": request_id})
                self.assertEqual(response.headers["X-Request-Id"], request_id)

    def test_request_id_is_generated(self):
        for headers in [{}, {"X-Request-Id": "x" * 129}, {"X-Request-Id": "bad value"}, {"X-Request-Id": "a/b"}]:
            with self.subTest(headers=headers):
                response = render(self.mock, headers=headers)
                self.assertRegex(response.headers["X-Request-Id"], GENERATED_REQUEST_ID)

    def test_request_id_on_rejected_requests(self):
        request_id = {"X-Request-Id": "req-1"}
        cases = [
            (400, {"data": "{}", "headers": {**JSON_HEADERS, **request_id}}),
            (404, {"path": "/nope", "headers": request_id}),
            (405, {"method": "GET", "headers": request_id}),
            (413, {"data": b" " * (MAX_BODY_BYTES + 1), "headers": request_id}),
            (415, {"data": json.dumps(VALID_REQUEST), "headers": request_id}),
        ]
        for status, kwargs in cases:
            with self.subTest(status=status):
                response = send(self.mock, **kwargs)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers["X-Request-Id"], "req-1")

    def test_request_id_by_scenario(self):
        cases = [
            ("success", True),
            ("render_failed", True),
            ("renderer_busy", True),
            ("internal_error", False),
            *((scenario, False) for scenario in INFRA_ERRORS),
        ]
        for scenario, echoed in cases:
            with self.subTest(scenario=scenario):
                self.mock.queue(scenario)
                response = render(self.mock, headers={"X-Request-Id": "req-1"})
                self.assertEqual(response.headers.get("X-Request-Id"), "req-1" if echoed else None)


class ChartExporterMockScenarioTests(ChartExporterMockTestCase):
    def test_errors(self):
        self.assertLessEqual(set(ERRORS), set(SCENARIOS))
        for scenario, (status, description) in ERRORS.items():
            with self.subTest(scenario=scenario):
                self.mock.queue(scenario)
                response = render(self.mock)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers["Content-Type"], "application/json")
                self.assertEqual(response.json(), {"errors": [{"code": scenario, "description": description}]})
                self.assertEqual("Retry-After" in response.headers, scenario == "renderer_busy")
                self.assertEqual(response.headers.get("Allow"), "POST" if scenario == "method_not_allowed" else None)

    def test_retry_after(self):
        self.mock.queue("renderer_busy")
        self.assertEqual(render(self.mock).headers["Retry-After"], "5")

        for queue_timeout, retry_after in [(0.1, "1"), (2, "2"), (7.6, "8")]:
            with (
                self.subTest(queue_timeout=queue_timeout),
                ChartExporterMock(default="renderer_busy", queue_timeout=queue_timeout) as mock,
            ):
                self.assertEqual(render(mock).headers["Retry-After"], retry_after)

    def test_infra_errors(self):
        self.assertEqual(INFRA_ERRORS, {"too_many_requests": 429, "bad_gateway": 502, "gateway_timeout": 504})
        for scenario, status in INFRA_ERRORS.items():
            with self.subTest(scenario=scenario):
                self.mock.queue(scenario)
                response = render(self.mock)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers["Content-Type"], "text/html")
                self.assertIn(f"<title>{status} ", response.text)
                with self.assertRaises(ValueError):
                    json.loads(response.content)

    def test_malformed_responses(self):
        self.mock.queue(*MALFORMED)
        responses = {scenario: render(self.mock) for scenario in MALFORMED}

        self.assertEqual({response.status_code for response in responses.values()}, {201})
        with self.assertRaises(ValueError):
            json.loads(responses["malformed_json"].content)
        self.assertEqual(list(responses["missing_fields"].json()), [f for f in RESPONSE_FIELDS if f != "key"])
        self.assertEqual(responses["invalid_id"].json()["id"], "not-a-uuid")
        self.assertEqual(responses["wrong_bucket"].json()["bucket"], "wrong-bucket")
        unexpected = responses["unexpected_key"].json()
        self.assertEqual(unexpected["bucket"], "ons-charts")
        self.assertFalse(unexpected["key"].startswith("charts/"))

    def test_delay(self):
        self.mock.set_default("success", delay=0.3)

        start = time.monotonic()
        response = render(self.mock)

        self.assertGreaterEqual(time.monotonic() - start, 0.3)
        self.assertEqual(response.status_code, 201)

    def test_delay_longer_than_client_timeout(self):
        self.mock.set_default("success", delay=0.3)

        with self.assertRaises(requests.exceptions.ReadTimeout):
            render(self.mock, timeout=0.1)

    def test_reset_releases_delayed_request(self):
        self.mock.set_default("success", delay=60)
        delayed = self.render_in_background(self.mock)
        self.wait_until(lambda: self.mock.in_flight == 1)

        self.mock.reset()

        self.assertIsInstance(delayed.exception(), requests.exceptions.ConnectionError)
        self.assertEqual(render(self.mock).status_code, 201)

    def test_hang(self):
        self.mock.set_default("hang")

        with self.assertRaises(requests.exceptions.ReadTimeout):
            render(self.mock, timeout=0.2)
        self.wait_until(lambda: self.mock.in_flight == 1)

    def test_reset_releases_a_hung_request(self):
        self.mock.set_default("hang")
        hung = self.render_in_background(self.mock)
        self.wait_until(lambda: self.mock.in_flight == 1)

        self.mock.reset()

        self.assertIsInstance(hung.exception(), requests.exceptions.ConnectionError)

    def test_drop(self):
        self.mock.queue("drop")

        with self.assertRaises(requests.exceptions.ConnectionError) as context:
            render(self.mock)

        self.assertNotIsInstance(context.exception, requests.exceptions.Timeout)
        self.assertEqual(self.mock.requests[-1].scenario, "drop")


class ChartExporterMockSequencingTests(ChartExporterMockTestCase):
    def statuses(self, count: int) -> list[int]:
        return [render(self.mock).status_code for _ in range(count)]

    def scenarios(self) -> list[str | None]:
        return [request.scenario for request in self.mock.requests]

    def test_queue_then_default(self):
        self.mock.queue("renderer_busy", "renderer_busy")

        self.assertEqual(self.statuses(4), [503, 503, 201, 201])

    def test_queue_specs(self):
        self.mock.queue("render_failed:0.2", {"scenario": "storage_failed", "delay": 0.1}, Behaviour("render_timeout"))
        self.assertEqual(
            self.mock.state()["queue"],
            [
                {"scenario": "render_failed", "delay": 0.2},
                {"scenario": "storage_failed", "delay": 0.1},
                {"scenario": "render_timeout", "delay": 0.0},
            ],
        )

        start = time.monotonic()
        codes = [render(self.mock).json()["errors"][0]["code"] for _ in range(3)]

        self.assertGreaterEqual(time.monotonic() - start, 0.3)
        self.assertEqual(codes, ["render_failed", "storage_failed", "render_timeout"])

    def test_set_default_delay_overrides_spec(self):
        self.mock.set_default("render_failed:2", delay=0)

        self.assertEqual(self.mock.state()["default"], {"scenario": "render_failed", "delay": 0})

    def test_fail_every(self):
        self.mock.fail_every(3)
        self.assertEqual(self.statuses(6), [201, 201, 503, 201, 201, 503])

        self.mock.fail_every(0)
        self.assertIsNone(self.mock.state()["fail_every"])
        self.assertEqual(self.statuses(3), [201, 201, 201])

    def test_precedence(self):
        self.mock.set_default("render_failed")
        self.mock.fail_every(2, "storage_failed")
        self.mock.queue("success", "success")

        self.assertEqual(self.statuses(5), [201, 201, 500, 500, 500])
        self.assertEqual(self.scenarios(), ["success", "success", "render_failed", "storage_failed", "render_failed"])

    def test_invalid_specs_are_rejected(self):
        for call in [
            partial(self.mock.set_default, "nope"),
            partial(self.mock.set_default, "success", delay=-1),
            partial(self.mock.queue, "success", "nope"),
            partial(self.mock.fail_every, -1),
            partial(self.mock.fail_every, 2, "nope"),
        ]:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()
        self.assertEqual(self.mock.state()["queue"], [])

    def test_reset_restores_constructor_default(self):
        with ChartExporterMock(default="render_failed") as mock:
            mock.set_default("success")
            mock.queue("renderer_busy")
            mock.fail_every(2)
            mock.set_health("CRITICAL")
            render(mock)

            mock.reset()

            self.assertEqual(
                mock.state(),
                {
                    "default": {"scenario": "render_failed", "delay": 0.0},
                    "queue": [],
                    "fail_every": None,
                    "health_status": "OK",
                    "request_count": 0,
                    "in_flight": 0,
                    "peak_in_flight": 0,
                    "scenarios": list(SCENARIOS),
                },
            )
            self.assertEqual(mock.requests, [])
            self.assert_errors(render(mock), 500, "render_failed")

    def test_reset_restarts_fail_every_count(self):
        self.mock.fail_every(2)
        render(self.mock)

        self.mock.reset()
        self.mock.fail_every(2)

        self.assertEqual(self.statuses(2), [201, 503])

    def test_concurrency_cap(self):
        with ChartExporterMock(default="hang", max_concurrent=1, queue_timeout=0.1) as mock:
            hung = self.render_in_background(mock)
            self.wait_until(lambda: mock.in_flight == 1)
            mock.set_default("success")

            start = time.monotonic()
            response = render(mock)

            self.assertGreaterEqual(time.monotonic() - start, 0.1)
            self.assert_errors(response, 503, "renderer_busy")
            self.assertEqual(response.headers["Retry-After"], "1")
            self.assertEqual(mock.peak_in_flight, 1)
            self.assertEqual([request.scenario for request in mock.requests], ["hang", "renderer_busy"])

            mock.reset()
            self.assertIsInstance(hung.exception(), requests.exceptions.ConnectionError)
            mock.set_default("success")
            self.assertEqual(render(mock).status_code, 201)

    def test_reset_drops_requests_waiting_for_a_slot(self):
        with ChartExporterMock(default="hang", max_concurrent=1, queue_timeout=TIMEOUT) as mock:
            hung = self.render_in_background(mock)
            self.wait_until(lambda: mock.in_flight == 1)
            waiting = self.render_in_background(mock)
            self.wait_until(lambda: len(mock.requests) > 1)  # the second request is waiting for the slot

            mock.reset()
            mock.queue("render_failed")

            self.assertIsInstance(hung.exception(), requests.exceptions.ConnectionError)
            self.assertIsInstance(waiting.exception(), requests.exceptions.ConnectionError)
            # The released request didn't take the behaviour queued after the reset.
            self.assert_errors(render(mock), 500, "render_failed")

    def test_peak_in_flight(self):
        count = 3
        self.mock.set_default("hang")
        hung = [self.render_in_background(self.mock) for _ in range(count)]
        self.wait_until(lambda: self.mock.in_flight == count)
        self.assertEqual(self.mock.peak_in_flight, count)

        self.mock.reset()

        for future in hung:
            self.assertIsInstance(future.exception(), requests.exceptions.ConnectionError)
        # Requests released by the reset don't count against the new state.
        self.assertEqual((self.mock.in_flight, self.mock.peak_in_flight), (0, 0))

    def test_records_requests(self):
        render(self.mock, headers={"X-Request-Id": "req-1"})
        self.mock.queue("render_failed")
        render(self.mock)
        send(self.mock, data="hello", headers={"Content-Type": "text/plain"})
        send(self.mock, "GET", "/health")

        recorded = self.mock.requests
        self.assertEqual(
            [(request.method, request.path, request.scenario) for request in recorded],
            [
                ("POST", "/charts", "success"),
                ("POST", "/charts", "render_failed"),
                ("POST", "/charts", None),
                ("GET", "/health", None),
            ],
        )
        self.assertEqual([request.body for request in recorded], [VALID_REQUEST, VALID_REQUEST, "hello", None])
        self.assertEqual(recorded[0].headers["content-type"], "application/json")
        self.assertEqual(recorded[0].headers["x-request-id"], "req-1")
        self.assertEqual(recorded[2].headers["content-type"], "text/plain")
        for request in recorded:
            self.assertEqual(list(request.headers), [name.lower() for name in request.headers])
        arrivals = [request.arrived_at for request in recorded]
        self.assertEqual(arrivals, sorted(arrivals))


class ChartExporterMockControlTests(ChartExporterMockTestCase):
    def health(self) -> requests.Response:
        return send(self.mock, "GET", "/health")

    def control(self, method: str, action: str, **kwargs: Any) -> requests.Response:
        return send(self.mock, method, f"{CONTROL_PREFIX}/{action}", **kwargs)

    def test_health(self):
        response = self.health()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        body = response.json()
        self.assertEqual(list(body), ["status", "version", "uptime", "start_time", "checks"])
        self.assertEqual(body["status"], "OK")
        self.assertEqual(list(body["version"]), ["version", "git_commit", "build_time", "language", "language_version"])
        self.assertIsInstance(body["uptime"], int)
        self.assertGreaterEqual(body["uptime"], 0)
        self.assertRegex(body["start_time"], r"T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z")
        self.assertEqual(datetime.fromisoformat(body["start_time"]).utcoffset(), timedelta(0))
        [check] = body["checks"]
        self.assertEqual(check["name"], "browser")
        self.assertEqual(check["status"], "OK")
        self.assertIsNone(check["status_code"])
        self.assertEqual(check["message"], "chromium browser is connected")
        self.assertRegex(check["last_checked"], r"\.\d{3}Z\Z")
        self.assertEqual(check["last_success"], check["last_checked"])
        self.assertIsNone(check["last_failure"])

    def test_unhealthy(self):
        for status, status_code in [("WARNING", 429), ("CRITICAL", 500)]:
            with self.subTest(status=status):
                self.mock.set_health(status)
                response = self.health()
                self.assertEqual(response.status_code, status_code)
                body = response.json()
                self.assertEqual(body["status"], status)
                [check] = body["checks"]
                self.assertEqual(check["status"], status)
                self.assertEqual(check["message"], "chromium browser is not connected")
                self.assertEqual(check["last_failure"], check["last_checked"])
                self.assertIsNone(check["last_success"])

    def test_health_history(self):
        last_success = self.health().json()["checks"][0]["last_success"]
        self.mock.set_health("CRITICAL")

        [check] = self.health().json()["checks"]
        self.assertEqual(check["last_success"], last_success)
        self.assertIsNotNone(check["last_failure"])

        self.mock.reset()
        [check] = self.health().json()["checks"]
        self.assertIsNone(check["last_failure"])

    def test_invalid_health_status(self):
        with self.assertRaises(ValueError):
            self.mock.set_health("DOWN")

    def test_configure(self):
        response = self.control(
            "POST",
            "configure",
            json={
                "default": "storage_failed",
                "queue": ["success", {"scenario": "renderer_busy", "delay": 0.1}],
                "fail_every": {"n": 4, "scenario": "render_timeout"},
                "health_status": "WARNING",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "default": {"scenario": "storage_failed", "delay": 0.0},
                "queue": [{"scenario": "success", "delay": 0.0}, {"scenario": "renderer_busy", "delay": 0.1}],
                "fail_every": {"n": 4, "scenario": "render_timeout", "delay": 0.0},
                "health_status": "WARNING",
                "request_count": 0,
                "in_flight": 0,
                "peak_in_flight": 0,
                "scenarios": list(SCENARIOS),
            },
        )
        self.assertEqual([render(self.mock).status_code for _ in range(5)], [201, 503, 500, 500, 500])
        self.assertEqual(
            [request.scenario for request in self.mock.requests],
            ["success", "renderer_busy", "storage_failed", "render_timeout", "storage_failed"],
        )
        self.assertEqual(self.health().status_code, 429)

        response = self.control("POST", "configure", json={"fail_every": None})
        self.assertIsNone(response.json()["fail_every"])

    def test_configure_invalid(self):
        cases = [
            {"default": "nope"},
            {"default": 3},
            {"queue": ["success:-1"]},
            {"fail_every": 3},
            {"fail_every": {"n": -1}},
            {"health_status": "DOWN"},
            {"bogus": 1},
            [],
            "x",
        ]
        for config in cases:
            with self.subTest(config=config):
                response = self.control("POST", "configure", json=config)
                self.assertEqual(response.status_code, 400)
                [error] = response.json()["errors"]
                self.assertEqual(error["code"], "invalid_mock_config")

        response = self.control("POST", "configure", data=b"{", headers=JSON_HEADERS)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["code"], "invalid_mock_config")

    def test_invalid_configure_changes_nothing(self):
        before = self.mock.state()

        response = self.control(
            "POST", "configure", json={"default": "render_failed", "queue": ["success"], "health_status": "DOWN"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.mock.state(), before)

    def test_requests(self):
        render(self.mock, headers={"X-Request-Id": "req-1"})

        response = self.control("GET", "requests")

        self.assertEqual(response.status_code, 200)
        [recorded] = response.json()
        self.assertEqual(list(recorded), ["method", "path", "headers", "body", "arrived_at", "scenario"])
        self.assertEqual((recorded["method"], recorded["path"]), ("POST", "/charts"))
        self.assertEqual(recorded["headers"]["x-request-id"], "req-1")
        self.assertEqual(recorded["body"], VALID_REQUEST)
        self.assertEqual(recorded["scenario"], "success")

    def test_reset(self):
        self.mock.set_default("storage_failed")
        self.mock.queue("render_failed")
        render(self.mock)

        response = self.control("POST", "reset")

        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual((state["default"]["scenario"], state["queue"], state["request_count"]), ("success", [], 0))
        self.assertEqual(self.mock.requests, [])

    def test_unknown_control_path(self):
        for method, action in [("GET", "nope"), ("GET", "configure"), ("POST", "requests"), ("GET", "")]:
            with self.subTest(method=method, action=action):
                self.assert_errors(self.control(method, action), 404, "not_found")

    def test_control_calls_are_not_recorded(self):
        self.control("POST", "configure", json={"default": "success"})
        self.control("GET", "requests")
        self.control("GET", "nope")

        self.assertEqual(self.mock.requests, [])


class BehaviourTests(SimpleTestCase):
    def test_parse(self):
        cases = [
            ("renderer_busy:1.5", Behaviour("renderer_busy", 1.5)),
            ("hang", Behaviour("hang", 0.0)),
            ({"scenario": "drop", "delay": 0.2}, Behaviour("drop", 0.2)),
            ({"scenario": "drop"}, Behaviour("drop")),
            (Behaviour("drop", 1), Behaviour("drop", 1)),
        ]
        for spec, expected in cases:
            with self.subTest(spec=spec):
                self.assertEqual(Behaviour.parse(spec), expected)

    def test_invalid(self):
        for scenario, delay in [("nope", 0), ("success", -0.1), ("success", math.inf), ("success", math.nan)]:
            with self.subTest(scenario=scenario, delay=delay), self.assertRaises(ValueError):
                Behaviour(scenario, delay)

        for spec in ["nope", "nope:1", "success:-1", "success:inf", "success:nan", "success:x", {"scenario": "nope"}]:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                Behaviour.parse(spec)

        for spec in [1, None, ["success"], {"scenario": "success", "bogus": 1}]:
            with self.subTest(spec=spec), self.assertRaises(TypeError):
                Behaviour.parse(spec)


class ChartExporterMockCommandLineTests(SimpleTestCase):
    def setUp(self):
        # Ignore any CHART_EXPORTER_MOCK_* variables set for the container, e.g. by a local .env.
        environ = {name: value for name, value in os.environ.items() if not name.startswith("CHART_EXPORTER_MOCK_")}
        self.enterContext(patch.dict(os.environ, environ, clear=True))

    def test_defaults(self):
        self.assertEqual(vars(parse_args([])), CLI_DEFAULTS)

    def test_flags(self):
        args = parse_args(
            shlex.split(
                "--host localhost --port 8000 --scenario hang --delay 0.5 --bucket my-bucket --key-prefix exports/ "
                "--output-dir media --max-concurrent 2 --queue-timeout 1.5 --quiet"
            )
        )

        self.assertEqual(vars(args), CLI_OPTIONS)

    def test_environment_variables(self):
        environ = {
            "CHART_EXPORTER_MOCK_HOST": "localhost",
            "CHART_EXPORTER_MOCK_PORT": "8000",
            "CHART_EXPORTER_MOCK_SCENARIO": "hang",
            "CHART_EXPORTER_MOCK_DELAY": "0.5",
            "CHART_EXPORTER_MOCK_BUCKET": "my-bucket",
            "CHART_EXPORTER_MOCK_KEY_PREFIX": "exports/",
            "CHART_EXPORTER_MOCK_OUTPUT_DIR": "media",
            "CHART_EXPORTER_MOCK_MAX_CONCURRENT": "2",
            "CHART_EXPORTER_MOCK_QUEUE_TIMEOUT": "1.5",
            "CHART_EXPORTER_MOCK_QUIET": "true",
        }
        with patch.dict(os.environ, environ):
            self.assertEqual(vars(parse_args([])), CLI_OPTIONS)
            self.assertEqual(parse_args(["--port", "9000"]).port, 9000)

    def test_invalid_scenario(self):
        for argv, environ in [(["--scenario", "nope"], {}), ([], {"CHART_EXPORTER_MOCK_SCENARIO": "nope"})]:
            with (
                self.subTest(argv=argv, environ=environ),
                patch.dict(os.environ, environ),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                parse_args(argv)

    def test_scenario_with_delay(self):
        self.assertEqual(parse_args(["--scenario", "render_failed:2"]).behaviour, Behaviour("render_failed", 2))
        self.assertEqual(
            parse_args(["--scenario", "render_failed:2", "--delay", "0.5"]).behaviour, Behaviour("render_failed", 0.5)
        )

    def test_quiet_environment_variable_ignores_case(self):
        with patch.dict(os.environ, {"CHART_EXPORTER_MOCK_QUIET": "True"}):
            self.assertTrue(parse_args([]).quiet)

    def test_mock_from_args(self):
        args = parse_args(shlex.split("--port 0 --scenario render_failed --delay 0.1 --quiet"))

        with mock_from_args(args) as mock:
            self.assertFalse(mock.log_requests)
            start = time.monotonic()
            response = render(mock)
            self.assertGreaterEqual(time.monotonic() - start, 0.1)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["errors"][0]["code"], "render_failed")

    def test_mock_from_args_options(self):
        args = parse_args(
            shlex.split("--port 0 --bucket my-bucket --key-prefix exports --max-concurrent 2 --queue-timeout 1.5")
        )

        with mock_from_args(args) as mock:
            self.assertTrue(mock.log_requests)
            self.assertEqual((mock.bucket, mock.key_prefix), ("my-bucket", "exports/"))
            self.assertEqual((mock.queue_timeout, mock.retry_after), (1.5, "2"))
            self.assertEqual(mock.state()["default"], {"scenario": "success", "delay": 0.0})

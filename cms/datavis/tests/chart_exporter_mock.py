"""A mock of the ONS chart exporter API for tests and local development.

It copies the HTTP contract of the real service (ONSdigital/design-system-chart-exporter): its routes,
request validation, error envelope, response shapes and headers. What it does with a valid render
request is a configurable "behaviour" (a scenario name plus an optional delay), so tests can get
errors, slow or hung responses, dropped connections and malformed responses on demand.

In-process::

    with ChartExporterMock() as mock:
        mock.queue("renderer_busy", "renderer_busy")  # the next two renders fail, then the default applies
        ...
        assert len(mock.requests) == 3

Standalone (see ``--help``)::

    python -m cms.datavis.tests.chart_exporter_mock --port 30300 --scenario success --delay 0.5

A running instance can be reconfigured over HTTP: ``POST /__mock__/configure``, ``GET /__mock__/requests``
and ``POST /__mock__/reset``.

This module only uses the standard library, so that it can run without Django.
"""

import argparse
import contextlib
import json
import os
import re
import struct
import sys
import threading
import time
import traceback
import uuid
import zlib
from collections import deque
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Self

MAX_BODY_BYTES = 1_048_576
DEFAULT_BUCKET = "ons-charts"
DEFAULT_KEY_PREFIX = "charts/"
CONTROL_PREFIX = "/__mock__"

# The real service's error codes, each with its HTTP status and description.
ERRORS: dict[str, tuple[int, str]] = {
    "invalid_language": (400, "language is required and must be 'en'."),
    "invalid_device": (400, "device is required and must be 'desktop'."),
    "invalid_chart_config": (400, "chart_config is required and must be a non-empty object."),
    "invalid_request_body": (
        400,
        "Request body must be a valid JSON object with language, device and chart_config.",
    ),
    "not_found": (404, "Not Found"),
    "method_not_allowed": (405, "Method Not Allowed"),
    "request_body_too_large": (413, f"Request body must not exceed {MAX_BODY_BYTES} bytes."),
    "unsupported_media_type": (415, "Content-Type must be application/json."),
    "render_failed": (500, "The chart could not be rendered."),
    "render_timeout": (500, "Chart rendering timed out."),
    "storage_failed": (500, "The rendered chart could not be stored."),
    "internal_error": (500, "An internal error occurred."),
    "renderer_busy": (503, "The service is busy rendering other charts; retry shortly."),
}
# Errors from the infrastructure in front of the service, which answers with HTML rather than JSON.
INFRA_ERRORS: dict[str, int] = {"too_many_requests": 429, "bad_gateway": 502, "gateway_timeout": 504}
# 201 responses that break the contract in one way each.
MALFORMED = ("malformed_json", "missing_fields", "invalid_id", "wrong_bucket", "unexpected_key")
SCENARIOS = ("success", *ERRORS, *INFRA_ERRORS, *MALFORMED, "hang", "drop")

HEALTH_STATUSES = {"OK": 200, "WARNING": 429, "CRITICAL": 500}
ROUTES = {"/charts": "POST", "/health": "GET"}
REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
REQUEST_FIELDS = frozenset({"language", "device", "chart_config"})


def _placeholder_png(width: int, height: int) -> bytes:
    """Build a plain grey greyscale PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)  # 8-bit greyscale
    pixels = (b"\x00" + b"\xcc" * width) * height  # each row: filter type 0, then the pixels
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


PNG_WIDTH, PNG_HEIGHT = 1200, 640
PNG = _placeholder_png(PNG_WIDTH, PNG_HEIGHT)


@dataclass(frozen=True)
class Behaviour:
    """What the mock does with a valid render request: wait ``delay`` seconds, then act out ``scenario``."""

    scenario: str = "success"
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario {self.scenario!r}. Expected one of: {', '.join(SCENARIOS)}")
        if not 0 <= self.delay < float("inf"):
            raise ValueError(f"delay must be a finite number of seconds >= 0, not {self.delay!r}")

    @classmethod
    def parse(cls, spec: str | dict[str, Any] | Behaviour) -> Behaviour:
        """Accept a Behaviour, a ``{"scenario": ..., "delay": ...}`` dict, or a ``"scenario[:delay]"`` string."""
        if isinstance(spec, Behaviour):
            return spec
        if isinstance(spec, dict):
            return cls(**spec)
        if not isinstance(spec, str):
            raise TypeError(f"Expected a behaviour, not {spec!r}")
        scenario, _, delay = spec.partition(":")
        return cls(scenario, float(delay or 0))


@dataclass
class RecordedRequest:
    """A request the mock received, other than calls to its control API."""

    method: str
    path: str  # as sent: "//charts" stays "//charts"
    headers: dict[str, str]  # lower-cased names
    body: Any  # the parsed JSON, else the decoded text, else None
    arrived_at: float  # time.time()
    scenario: str | None = None  # the behaviour applied, or None if the request was rejected before rendering


@dataclass
class _State:
    """Everything reset() clears."""

    default: Behaviour
    queue: deque[Behaviour] = field(default_factory=deque)
    fail_every: tuple[int, Behaviour] | None = None
    requests: list[RecordedRequest] = field(default_factory=list)
    render_count: int = 0
    in_flight: int = 0
    peak_in_flight: int = 0
    health_status: str = "OK"
    last_success: str | None = None
    last_failure: str | None = None

    def next_behaviour(self) -> Behaviour:
        self.render_count += 1
        if self.queue:
            return self.queue.popleft()
        if self.fail_every and self.render_count % self.fail_every[0] == 0:
            return self.fail_every[1]
        return self.default


class ChartExporterMock:
    """A mock chart exporter, served from a background thread.

    The behaviour for each valid ``POST /charts`` is, in order of precedence: the next queued behaviour,
    the ``fail_every`` behaviour if this render is a multiple of its ``n``, then the default.
    If ``max_concurrent`` is set, renders beyond it wait up to ``queue_timeout`` seconds for a slot and
    then get ``503 renderer_busy``, like the real service. With ``output_dir``, each successful render
    also writes the placeholder PNG to ``output_dir/<key>``.
    """

    def __init__(  # noqa: PLR0913  # pylint: disable=too-many-arguments
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        default: str | Behaviour = "success",
        bucket: str = DEFAULT_BUCKET,
        key_prefix: str = DEFAULT_KEY_PREFIX,
        output_dir: str | os.PathLike[str] | None = None,
        max_concurrent: int | None = None,
        queue_timeout: float = 5.0,
    ) -> None:
        self.bucket = bucket
        self.key_prefix = key_prefix if not key_prefix or key_prefix.endswith("/") else f"{key_prefix}/"
        self.output_dir = Path(output_dir) if output_dir else None
        self.queue_timeout = queue_timeout
        self.retry_after = str(max(1, round(queue_timeout)))
        self.log_requests = False
        self._initial_default = Behaviour.parse(default)
        self._state = _State(self._initial_default)
        self._slots = threading.BoundedSemaphore(max_concurrent) if max_concurrent else None
        self._lock = threading.Lock()
        self._release = threading.Event()
        self._started_at = datetime.now(UTC)
        self._server = _Server((host, port), self)
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> Self:
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, name="chart-exporter-mock", daemon=True
        )
        self._thread.start()
        return self

    def stop(self) -> None:
        """Release delayed and hung requests, stop serving, and wait for in-progress requests to finish."""
        with self._lock:
            self._release.set()
        if self._thread:
            self._server.shutdown()
            self._thread.join()
            self._thread = None
        self._server.server_close()

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def reset(self) -> None:
        """Forget recorded requests and configuration, and release delayed and hung requests.

        Released requests drop their connection without responding or writing a file.
        """
        with self._lock:
            self._release.set()
            self._release = threading.Event()
            self._state = _State(self._initial_default)

    def set_default(self, spec: str | dict[str, Any] | Behaviour, delay: float | None = None) -> None:
        """Set the behaviour used when nothing is queued, e.g. ``set_default("render_failed", delay=1)``."""
        behaviour = _behaviour(spec, delay)
        with self._lock:
            self._state.default = behaviour

    def queue(self, *specs: str | dict[str, Any] | Behaviour) -> None:
        """Queue behaviours for the next renders, in order. After the queue empties, the default applies."""
        behaviours = [Behaviour.parse(spec) for spec in specs]
        with self._lock:
            self._state.queue.extend(behaviours)

    def fail_every(
        self, n: int, scenario: str | dict[str, Any] | Behaviour = "renderer_busy", delay: float | None = None
    ) -> None:
        """Apply ``scenario`` to every ``n``th render (counting from the last reset) instead of the default.

        ``n=0`` turns this off.
        """
        rule = _fail_every_rule(n, scenario, delay)
        with self._lock:
            self._state.fail_every = rule

    def set_health(self, status: str) -> None:
        _check_health_status(status)
        with self._lock:
            self._state.health_status = status

    def configure(self, config: dict[str, Any]) -> None:
        """Apply a control API config: ``default``, ``queue`` (appended), ``fail_every`` and/or ``health_status``.

        Nothing changes unless the whole config is valid.
        """
        if not isinstance(config, dict):
            raise TypeError("The config must be a JSON object")
        if unknown := set(config) - {"default", "queue", "fail_every", "health_status"}:
            raise ValueError(f"Unknown config keys: {', '.join(sorted(unknown))}")
        changes: dict[str, Any] = {}
        if "default" in config:
            changes["default"] = Behaviour.parse(config["default"])
        if "fail_every" in config:
            changes["fail_every"] = _fail_every_rule(**(config["fail_every"] or {"n": 0}))
        if "health_status" in config:
            changes["health_status"] = _check_health_status(config["health_status"])
        queued = [Behaviour.parse(spec) for spec in config.get("queue", [])]
        with self._lock:
            for name, value in changes.items():
                setattr(self._state, name, value)
            self._state.queue.extend(queued)

    @property
    def requests(self) -> list[RecordedRequest]:
        """The requests received since the last reset, oldest first."""
        with self._lock:
            return list(self._state.requests)

    @property
    def in_flight(self) -> int:
        """The renders in progress, not counting any that the last reset released."""
        with self._lock:
            return self._state.in_flight

    @property
    def peak_in_flight(self) -> int:
        """The most renders in progress at once since the last reset."""
        with self._lock:
            return self._state.peak_in_flight

    def state(self) -> dict[str, Any]:
        with self._lock:
            state = self._state
            fail_every = state.fail_every and {"n": state.fail_every[0], **asdict(state.fail_every[1])}
            return {
                "default": asdict(state.default),
                "queue": [asdict(behaviour) for behaviour in state.queue],
                "fail_every": fail_every,
                "health_status": state.health_status,
                "request_count": len(state.requests),
                "in_flight": state.in_flight,
                "peak_in_flight": state.peak_in_flight,
                "scenarios": list(SCENARIOS),
            }

    # The methods below are called by the request handler.

    def record(self, request: RecordedRequest) -> None:
        with self._lock:
            self._state.requests.append(request)

    @contextlib.contextmanager
    def render_slot(self) -> Iterator[tuple[Behaviour, threading.Event] | None]:
        """Take a render slot, counting the request as in flight, and pick its behaviour.

        Yields the behaviour with the event that reset() and stop() will set, or None if no slot became free.
        A request that reset() or stop() released while it waited for a slot gets "drop".
        """
        with self._lock:
            release = self._release
        acquired = not self._slots or self._slots.acquire(timeout=self.queue_timeout)
        with self._lock:
            state: _State | None = self._state  # count against this state, even if reset() replaces it
            if release.is_set():
                state, picked = None, (Behaviour("drop"), release)
            elif not acquired:
                state, picked = None, None
            else:
                state.in_flight += 1
                state.peak_in_flight = max(state.peak_in_flight, state.in_flight)
                # Under the same lock, so a request counted in in_flight can't pick up a later configuration.
                picked = state.next_behaviour(), release
        try:
            yield picked
        finally:
            if state:
                with self._lock:
                    state.in_flight -= 1
            if acquired and self._slots:
                self._slots.release()

    def render_response(self, scenario: str) -> bytes:
        """The 201 body for "success" or one of the MALFORMED scenarios. Writes the PNG on success."""
        if scenario == "malformed_json":
            return b"{not json"
        chart_id = str(uuid.uuid4())
        body: dict[str, Any] = {
            "id": chart_id,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "bucket": self.bucket,
            "key": f"{self.key_prefix}{chart_id}.png",
            "content_type": "image/png",
            "size_bytes": len(PNG),
            "width": PNG_WIDTH,
            "height": PNG_HEIGHT,
        }
        match scenario:
            case "success" if self.output_dir:
                path = self.output_dir / body["key"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(PNG)
            case "missing_fields":
                del body["key"]
            case "invalid_id":
                body["id"] = "not-a-uuid"
            case "wrong_bucket":
                body["bucket"] = "wrong-bucket"
            case "unexpected_key":
                body["key"] = f"unexpected/{chart_id}.png"
        return _json(body)

    def health(self) -> tuple[int, bytes]:
        """The status code and body for ``GET /health``, in the DP health check shape."""
        now = datetime.now(UTC)
        checked_at = _timestamp(now)
        with self._lock:
            state = self._state
            status = state.health_status
            if status == "OK":
                state.last_success = checked_at
            else:
                state.last_failure = checked_at
            last_success, last_failure = state.last_success, state.last_failure
        body = {
            "status": status,
            "version": {
                "version": "mock",
                "git_commit": "",
                "build_time": "",
                "language": "python",
                "language_version": sys.version.split()[0],
            },
            "uptime": int((now - self._started_at).total_seconds() * 1000),
            "start_time": _timestamp(self._started_at),
            "checks": [
                {
                    "name": "browser",
                    "status": status,
                    "status_code": None,
                    "message": f"chromium browser is {'connected' if status == 'OK' else 'not connected'}",
                    "last_checked": checked_at,
                    "last_success": last_success,
                    "last_failure": last_failure,
                }
            ],
        }
        return HEALTH_STATUSES[status], _json(body)


class _Server(ThreadingHTTPServer):
    daemon_threads = False  # so server_close() waits for the handler threads

    def __init__(self, address: tuple[str, int], mock: ChartExporterMock) -> None:
        self.mock = mock
        super().__init__(address, _Handler)

    def handle_error(self, request: Any, client_address: Any) -> None:
        if isinstance(sys.exc_info()[1], ConnectionError | TimeoutError):
            return  # the client hung up first (e.g. after its read timeout), or stalled mid-request
        super().handle_error(request, client_address)


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    timeout = 10  # seconds before giving up on a client that stalls mid-request
    request_id = ""

    def _dispatch(self) -> None:
        try:
            self._handle()
        except ConnectionError, TimeoutError:
            raise
        except Exception:  # pylint: disable=broad-exception-caught
            # Answer, so that a bug in the mock can't pass for the "drop" scenario.
            traceback.print_exc()
            self._send_errors(500, [{"code": "mock_error", "description": "The chart exporter mock failed."}])

    # The real service answers any method. Route the common ones here rather than leave them to http.server's 501.
    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _dispatch

    def _handle(self) -> None:
        arrived_at = time.time()
        # parse_request() has already collapsed a leading "//" in self.path. The real service doesn't,
        # so route on the path as sent.
        path = self.requestline.split()[1].partition("?")[0]
        if path.startswith(CONTROL_PREFIX):
            self._handle_control(path.removeprefix(CONTROL_PREFIX))
            return

        inbound_id = self.headers.get("X-Request-Id", "")
        self.request_id = inbound_id if REQUEST_ID.fullmatch(inbound_id) else uuid.uuid4().hex
        content_length = self.headers.get("Content-Length", "")
        too_large = content_length.isdigit() and int(content_length) > MAX_BODY_BYTES
        body = b"" if too_large else self._read_body()
        record = RecordedRequest(
            method=self.command,
            path=path,
            headers={name.lower(): value for name, value in self.headers.items()},
            body=_decode_for_record(body),
            arrived_at=arrived_at,
        )
        self.server.mock.record(record)

        if too_large:
            self._send_error("request_body_too_large")
            self._discard_body(int(content_length))
        elif path not in ROUTES:
            self._send_error("not_found")
        elif self.command != ROUTES[path]:
            self._send_error("method_not_allowed", {"Allow": ROUTES[path]})
        elif path == "/health":
            status, health = self.server.mock.health()
            self._send(status, health)
        elif invalid := check_render_request(self.headers.get("Content-Type", ""), body):
            self._send_errors(*invalid)
        else:
            self._render(record)

    def _render(self, record: RecordedRequest) -> None:
        mock = self.server.mock
        with mock.render_slot() as picked:
            if picked is None:
                record.scenario = "renderer_busy"
                self._send_error("renderer_busy")
                return
            behaviour, released = picked
            record.scenario = behaviour.scenario
            if behaviour.delay and released.wait(behaviour.delay):
                return  # released by reset() or stop(): drop the connection
            match behaviour.scenario:
                case "hang":
                    released.wait()
                case "drop":
                    pass  # returning without a response closes the connection
                case scenario if scenario in ERRORS:
                    self._send_error(scenario)
                case scenario if scenario in INFRA_ERRORS:
                    self._send_infra_error(INFRA_ERRORS[scenario])
                case scenario:
                    self._send(201, mock.render_response(scenario))

    def _handle_control(self, action: str) -> None:
        mock = self.server.mock
        match self.command, action:
            case "GET", "/requests":
                self._send(200, _json([asdict(request) for request in mock.requests]))
            case "POST", "/reset":
                mock.reset()
                self._send(200, _json(mock.state()))
            case "POST", "/configure":
                try:
                    mock.configure(json.loads(self._read_body() or b"{}"))
                except (TypeError, ValueError) as error:
                    self._send_errors(400, [{"code": "invalid_mock_config", "description": str(error)}])
                else:
                    self._send(200, _json(mock.state()))
            case _:
                self._send_error("not_found")

    def _read_body(self) -> bytes:
        content_length = self.headers.get("Content-Length", "")
        return self.rfile.read(int(content_length)) if content_length.isdigit() else b""

    def _discard_body(self, length: int) -> None:
        """Read and drop a body that has been answered, so that a client still sending it doesn't get a reset."""
        with contextlib.suppress(OSError):
            while length > 0 and (chunk := self.rfile.read(min(length, 65536))):
                length -= len(chunk)

    def _send(
        self, status: int, body: bytes, content_type: str = "application/json", headers: dict[str, str] | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if self.request_id:
            self.send_header("X-Request-Id", self.request_id)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_errors(self, status: int, errors: list[dict[str, str]], headers: dict[str, str] | None = None) -> None:
        self._send(status, _json({"errors": errors}), headers=headers)

    def _send_error(self, code: str, headers: dict[str, str] | None = None) -> None:
        status, description = ERRORS[code]
        if code == "renderer_busy":
            headers = {"Retry-After": self.server.mock.retry_after}
        elif code == "method_not_allowed":
            headers = headers or {"Allow": "POST"}  # as a behaviour, it can only be answering POST /charts
        elif code == "internal_error":
            # The real service sends unhandled errors from outside the middleware that adds X-Request-Id.
            self.request_id = ""
        self._send_errors(status, [{"code": code, "description": description}], headers)

    def _send_infra_error(self, status: int) -> None:
        title = f"{status} {HTTPStatus(status).phrase}"
        self.request_id = ""  # generated by the load balancer, which knows nothing of the request ID
        html = f"<html><head><title>{title}</title></head><body><center><h1>{title}</h1></center></body></html>\n"
        self._send(status, html.encode(), "text/html")

    def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        if self.server.mock.log_requests:
            super().log_message(format, *args)


def check_render_request(content_type: str, body: bytes) -> tuple[int, list[dict[str, str]]] | None:
    """Validate a ``POST /charts`` request as the real service does.

    Returns the status and errors to respond with, or None if the request is valid.
    """
    media_type = content_type.split(";", 1)[0].strip().lower()
    payload: Any = None
    # Like FastAPI, parse any JSON-ish body before checking the media type exactly.
    if body and (media_type == "application/json" or re.fullmatch(r"application/[^/]+\+json", media_type)):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return 400, [_error("invalid_request_body")]
        except ValueError, RecursionError:  # e.g. the body isn't UTF-8
            return 400, [{"code": "http_error", "description": "There was an error parsing the body"}]
    if media_type != "application/json":
        return 415, [_error("unsupported_media_type")]

    if not isinstance(payload, dict):
        return 400, [_error("invalid_request_body")]
    codes = []  # in the order pydantic reports them
    if payload.get("language") != "en":
        codes.append("invalid_language")
    if payload.get("device") != "desktop":
        codes.append("invalid_device")
    if not isinstance(payload.get("chart_config"), dict) or not payload["chart_config"]:
        codes.append("invalid_chart_config")
    if set(payload) - REQUEST_FIELDS:
        codes.append("invalid_request_body")
    return (400, [_error(code) for code in codes]) if codes else None


def _error(code: str) -> dict[str, str]:
    return {"code": code, "description": ERRORS[code][1]}


def _behaviour(spec: str | dict[str, Any] | Behaviour, delay: float | None) -> Behaviour:
    behaviour = Behaviour.parse(spec)
    return behaviour if delay is None else replace(behaviour, delay=delay)


def _fail_every_rule(
    n: int, scenario: str | dict[str, Any] | Behaviour = "renderer_busy", delay: float | None = None
) -> tuple[int, Behaviour] | None:
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"n must be a whole number >= 0, not {n!r}")
    return (n, _behaviour(scenario, delay)) if n else None


def _check_health_status(status: str) -> str:
    if status not in HEALTH_STATUSES:
        raise ValueError(f"Unknown health status {status!r}. Expected one of: {', '.join(HEALTH_STATUSES)}")
    return status


def _json(data: Any) -> bytes:
    return json.dumps(data, separators=(",", ":")).encode()


def _decode_for_record(body: bytes) -> Any:
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError, RecursionError:
        return body.decode(errors="replace")


def _timestamp(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _env(option: str, default: str) -> str:
    return os.environ.get(f"CHART_EXPORTER_MOCK_{option}", default)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m cms.datavis.tests.chart_exporter_mock",
        description="Run a mock ONS chart exporter API. Each option can also be set with an environment variable, "
        "e.g. CHART_EXPORTER_MOCK_PORT or CHART_EXPORTER_MOCK_KEY_PREFIX.",
    )
    parser.add_argument("--host", default=_env("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=_env("PORT", "30300"))
    parser.add_argument(
        "--scenario",
        default=_env("SCENARIO", "success"),
        help=f"default behaviour, optionally with a delay (e.g. render_failed:2). One of: {', '.join(SCENARIOS)}",
    )
    parser.add_argument("--delay", type=float, default=_env("DELAY", "") or None, help="overrides the --scenario delay")
    parser.add_argument("--bucket", default=_env("BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--key-prefix", default=_env("KEY_PREFIX", DEFAULT_KEY_PREFIX))
    parser.add_argument(
        "--output-dir", default=_env("OUTPUT_DIR", "") or None, help="write rendered PNGs to <output-dir>/<key>"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=_env("MAX_CONCURRENT", "") or None,
        help="render slots; further renders wait --queue-timeout seconds for one, then get 503",
    )
    parser.add_argument("--queue-timeout", type=float, default=_env("QUEUE_TIMEOUT", "5"))
    parser.add_argument(
        "--quiet", action="store_true", default=_env("QUIET", "").lower() == "true", help="don't log requests"
    )
    args = parser.parse_args(argv)
    try:
        args.behaviour = _behaviour(args.scenario, args.delay)
    except ValueError as error:
        parser.error(str(error))
    return args


def mock_from_args(args: argparse.Namespace) -> ChartExporterMock:
    mock = ChartExporterMock(
        host=args.host,
        port=args.port,
        default=args.behaviour,
        bucket=args.bucket,
        key_prefix=args.key_prefix,
        output_dir=args.output_dir,
        max_concurrent=args.max_concurrent,
        queue_timeout=args.queue_timeout,
    )
    mock.log_requests = not args.quiet
    return mock


def main(argv: Sequence[str] | None = None) -> None:
    mock = mock_from_args(parse_args(argv))
    with mock, contextlib.suppress(KeyboardInterrupt):
        print(f"Chart exporter mock listening on {mock.url}, control API at {mock.url}{CONTROL_PREFIX}/", flush=True)
        threading.Event().wait()


if __name__ == "__main__":
    main()

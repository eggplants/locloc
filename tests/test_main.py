from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import status
from git.exc import GitCommandError
from timeout_decorator import (  # type: ignore[import-not-found]
    TimeoutError as TDTimeoutError,
)

from locloc import __version__
from locloc.main import app, main

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from locloc.loc import Total, TotalByLanguageDict

REPO_URL = "https://github.com/eggplants/locloc"
SVG_BYTES = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
EXPECTED_PORT = 5000


@pytest.fixture
def stub_stats(
    monkeypatch: pytest.MonkeyPatch,
    stats: TotalByLanguageDict,
    total: Total,
) -> list[dict[str, Any]]:
    """Replace the git/tokei pipeline with a stub, recording the arguments it receives."""
    calls: list[dict[str, Any]] = []

    def fake_get_loc_stats(url: Any, branch: Any = None) -> tuple[TotalByLanguageDict, Total]:  # noqa: ANN401
        calls.append({"url": url, "branch": branch})
        return stats, total

    monkeypatch.setattr("locloc.main.get_loc_stats", fake_get_loc_stats)
    monkeypatch.setattr("locloc.main.get_loc_svg", lambda _result: SVG_BYTES)
    return calls


@pytest.fixture
def failing_stats(monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: ANN401
    """Return a helper that makes :func:`locloc.main.get_loc_stats` raise the given exception."""

    def _fail(exc: BaseException) -> None:
        def fake_get_loc_stats(url: Any, branch: Any = None) -> None:  # noqa: ANN401, ARG001
            raise exc

        monkeypatch.setattr("locloc.main.get_loc_stats", fake_get_loc_stats)

    return _fail


class TestHealthcheck:
    def test_get_returns_ok(self, client: TestClient) -> None:
        response = client.get("/healthcheck")

        assert response.status_code == status.HTTP_200_OK
        assert response.text == "OK"
        assert response.headers["content-type"].startswith("text/plain")

    def test_head_is_supported(self, client: TestClient) -> None:
        assert client.head("/healthcheck").status_code == status.HTTP_200_OK

    def test_post_is_rejected(self, client: TestClient) -> None:
        assert client.post("/healthcheck").status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestRoot:
    def test_renders_the_index_template(self, client: TestClient) -> None:
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")
        assert "<title>locloc</title>" in response.text

    def test_embeds_the_package_version(self, client: TestClient) -> None:
        assert __version__ in client.get("/").text

    def test_head_is_supported(self, client: TestClient) -> None:
        assert client.head("/").status_code == status.HTTP_200_OK

    def test_unknown_path_is_not_found(self, client: TestClient) -> None:
        assert client.get("/does-not-exist").status_code == status.HTTP_404_NOT_FOUND


class TestStaticFiles:
    @pytest.mark.parametrize(
        ("path", "content_type"),
        [
            ("/static/index.css", "text/css"),
            ("/static/index.js", "javascript"),
            ("/static/favicon.png", "image/png"),
        ],
    )
    def test_assets_are_served(self, client: TestClient, path: str, content_type: str) -> None:
        response = client.get(path)

        assert response.status_code == status.HTTP_200_OK
        assert content_type in response.headers["content-type"]

    def test_missing_asset_is_not_found(self, client: TestClient) -> None:
        assert client.get("/static/nope.css").status_code == status.HTTP_404_NOT_FOUND


class TestRes:
    def test_returns_stats_without_svg_by_default(
        self,
        client: TestClient,
        stub_stats: list[dict[str, Any]],
        stats: TotalByLanguageDict,
        total: Total,
    ) -> None:
        response = client.get("/res", params={"url": REPO_URL})

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["result"] == stats.model_dump()
        assert body["total"] == total.model_dump()
        assert body["svg"] is None
        assert len(stub_stats) == 1

    @pytest.mark.usefixtures("stub_stats")
    def test_returns_svg_when_requested(self, client: TestClient) -> None:
        response = client.get("/res", params={"url": REPO_URL, "is_svg": "true"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["svg"] == SVG_BYTES.decode()

    def test_passes_the_url_through(self, client: TestClient, stub_stats: list[dict[str, Any]]) -> None:
        client.get("/res", params={"url": REPO_URL})

        assert str(stub_stats[0]["url"]).rstrip("/") == REPO_URL

    def test_passes_the_branch_through(self, client: TestClient, stub_stats: list[dict[str, Any]]) -> None:
        client.get("/res", params={"url": REPO_URL, "branch": "develop"})

        assert stub_stats[0]["branch"] == "develop"

    @pytest.mark.parametrize("branch", ["", None])
    def test_blank_branch_falls_back_to_the_default(
        self,
        client: TestClient,
        stub_stats: list[dict[str, Any]],
        branch: str | None,
    ) -> None:
        params = {"url": REPO_URL} if branch is None else {"url": REPO_URL, "branch": branch}
        client.get("/res", params=params)

        assert stub_stats[0]["branch"] is None

    def test_url_is_required(self, client: TestClient) -> None:
        assert client.get("/res").status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize("url", ["not-a-url", "ftp://example.com/repo", ""])
    def test_invalid_url_is_rejected(self, client: TestClient, url: str) -> None:
        assert client.get("/res", params={"url": url}).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_overlong_url_is_rejected(self, client: TestClient) -> None:
        long_url = "https://example.com/" + "a" * 255

        assert client.get("/res", params={"url": long_url}).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_overlong_branch_is_rejected(self, client: TestClient) -> None:
        response = client.get("/res", params={"url": REPO_URL, "branch": "b" * 256})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_git_failure_becomes_bad_request(self, client: TestClient, failing_stats: Any) -> None:  # noqa: ANN401
        failing_stats(GitCommandError("git clone", 128))

        assert client.get("/res", params={"url": REPO_URL}).status_code == status.HTTP_400_BAD_REQUEST

    def test_timeout_becomes_request_timeout(self, client: TestClient, failing_stats: Any) -> None:  # noqa: ANN401
        failing_stats(TDTimeoutError("too slow"))

        assert client.get("/res", params={"url": REPO_URL}).status_code == status.HTTP_408_REQUEST_TIMEOUT


class TestSvg:
    @pytest.mark.usefixtures("stub_stats")
    def test_returns_an_svg_document(self, client: TestClient) -> None:
        response = client.get("/svg", params={"url": REPO_URL})

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert response.content == SVG_BYTES
        assert ET.fromstring(response.content) is not None  # noqa: S314 - fixture content

    @pytest.mark.usefixtures("stub_stats")
    def test_sets_caching_headers(self, client: TestClient) -> None:
        headers = client.get("/svg", params={"url": REPO_URL}).headers

        assert "max-age=3666" in headers["cache-control"]
        assert headers["pragma"] == "no-cache"
        assert headers["expires"].endswith("GMT")

    def test_passes_the_branch_through(self, client: TestClient, stub_stats: list[dict[str, Any]]) -> None:
        client.get("/svg", params={"url": REPO_URL, "branch": "develop"})

        assert stub_stats[0]["branch"] == "develop"

    def test_blank_branch_falls_back_to_the_default(
        self,
        client: TestClient,
        stub_stats: list[dict[str, Any]],
    ) -> None:
        client.get("/svg", params={"url": REPO_URL, "branch": ""})

        assert stub_stats[0]["branch"] is None

    def test_url_is_required(self, client: TestClient) -> None:
        assert client.get("/svg").status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_git_failure_becomes_bad_request(self, client: TestClient, failing_stats: Any) -> None:  # noqa: ANN401
        failing_stats(GitCommandError("git clone", 128))

        assert client.get("/svg", params={"url": REPO_URL}).status_code == status.HTTP_400_BAD_REQUEST

    def test_timeout_becomes_request_timeout(self, client: TestClient, failing_stats: Any) -> None:  # noqa: ANN401
        failing_stats(TDTimeoutError("too slow"))

        assert client.get("/svg", params={"url": REPO_URL}).status_code == status.HTTP_408_REQUEST_TIMEOUT


class TestEntryPoint:
    @pytest.fixture
    def served(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
        """Capture the uvicorn configuration instead of actually binding a port."""
        captured: dict[str, Any] = {}

        class FakeConfig:
            def __init__(self, application: Any, **kwargs: Any) -> None:  # noqa: ANN401
                captured["app"] = application
                captured.update(kwargs)

        class FakeServer:
            def __init__(self, config: FakeConfig) -> None:
                captured["config"] = config

            def run(self) -> None:
                captured["ran"] = True

        monkeypatch.setattr("uvicorn.Config", FakeConfig)
        monkeypatch.setattr("uvicorn.Server", FakeServer)
        return captured

    def test_serves_the_app_on_port_5000(self, served: dict[str, Any]) -> None:
        main()

        assert served["app"] is app
        assert served["port"] == EXPECTED_PORT
        assert served["log_level"] == "info"
        assert served["ran"] is True

    def test_reload_is_off_without_debug(self, served: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEBUG", raising=False)
        main()

        assert served["reload"] is False

    def test_reload_follows_the_debug_environment_variable(
        self,
        served: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DEBUG", "1")
        main()

        assert served["reload"] is True

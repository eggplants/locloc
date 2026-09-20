from __future__ import annotations

import importlib
import importlib.metadata
import re
from typing import TYPE_CHECKING

import locloc
from locloc import __version__, app

if TYPE_CHECKING:
    import pytest


def test_version_is_exposed() -> None:
    assert __version__ is not None


def test_version_looks_like_a_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", __version__)


def test_public_api() -> None:
    assert locloc.__all__ == ("__version__", "app")
    assert all(hasattr(locloc, name) for name in locloc.__all__)


def test_app_is_the_asgi_application() -> None:
    assert callable(app)
    assert app is locloc.cli.app


def test_routes_are_registered() -> None:
    paths = {getattr(route, "path", None) for route in app.routes}

    assert {"/", "/res", "/svg", "/healthcheck", "/static"} <= paths


def test_version_falls_back_when_the_package_is_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_found(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", raise_not_found)
    reloaded = importlib.reload(locloc)
    try:
        assert reloaded.__version__ == "0.0.0"
    finally:
        monkeypatch.undo()
        importlib.reload(locloc)

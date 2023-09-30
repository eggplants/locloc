from __future__ import annotations

from locloc import __version__


def check_version() -> None:
    assert __version__ is not None

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from git.repo import Repo

from locloc.loc import Total, TotalByLanguageDict
from locloc.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

PYTHON_SOURCE = '''"""Docstring."""

# a comment


def hello() -> str:
    return "hello"


def world() -> str:
    return "world"
'''

JAVASCRIPT_SOURCE = """// a comment
const hello = () => "hello";

const world = () => "world";
"""


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ``TemporaryDirectory(dir=".")`` in :func:`locloc.loc.get_loc_stats` out of the repo."""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sample_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real local git repository with a ``main`` and a ``other`` branch."""
    repo_path = tmp_path_factory.mktemp("sample_repo")
    env = {
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "tester@example.com",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "tester@example.com",
        **os.environ,
    }
    repo = Repo.init(repo_path, initial_branch="main")
    with repo.git.custom_environment(**env):
        (repo_path / "hello.py").write_text(PYTHON_SOURCE)
        (repo_path / "hello.js").write_text(JAVASCRIPT_SOURCE)
        repo.index.add(["hello.py", "hello.js"])
        repo.index.commit("initial commit")

        repo.create_head("other")
        repo.heads.other.checkout()
        (repo_path / "extra.py").write_text(PYTHON_SOURCE)
        repo.index.add(["extra.py"])
        repo.index.commit("branch-only commit")
        repo.heads.main.checkout()

    return repo_path


@pytest.fixture
def stats() -> TotalByLanguageDict:
    """A small, deterministic statistics payload."""
    return TotalByLanguageDict.model_validate(
        {
            "Python": Total(lines=100, blanks=10, code=80, files=3, comments=10),
            "JavaScript": Total(lines=40, blanks=5, code=30, files=1, comments=5),
            "Markdown": Total(lines=7, blanks=2, code=0, files=1, comments=5),
        },
    )


@pytest.fixture
def total() -> Total:
    return Total(lines=147, blanks=17, code=110, files=5, comments=20)

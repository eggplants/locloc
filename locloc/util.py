from __future__ import annotations

from tempfile import TemporaryDirectory

from git.repo import Repo
from pydantic import BaseModel, RootModel
from pytokei import Config, Languages


class Total(BaseModel):
    lines: int
    blanks: int
    code: int
    files: int
    comments: int


TotalByLanguageDict = RootModel[dict[str, Total]]


def get_loc_stats() -> tuple[TotalByLanguageDict, Total]:
    with TemporaryDirectory(prefix="tmp_", dir=".") as tmpdir_path:
        repo = Repo.clone_from(
            url="https://github.com/eggplants/getjump",
            to_path=tmpdir_path,
            depth=1,
            branch="master",
        )
        langs = Languages()
        langs.get_statistics(paths=[str(repo.working_dir)], ignored=[], config=Config())
    result = TotalByLanguageDict.model_validate(langs.report_compact_plain())
    total = Total.model_validate(langs.total_plain())
    return result, total

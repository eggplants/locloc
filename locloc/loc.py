from __future__ import annotations

from tempfile import TemporaryDirectory

from git.repo import Repo
from pydantic import BaseModel, HttpUrl, RootModel
from pygal import HorizontalBar  # type: ignore[import,unused-ignore]
from pytokei import Config, Languages
from timeout_decorator import timeout  # type: ignore[import,unused-ignore]


class Total(BaseModel):
    lines: int
    blanks: int
    code: int
    files: int
    comments: int


TotalByLanguageDict = RootModel[dict[str, Total]]

__TIMEOUT_SECONDS = 30.0


@timeout(__TIMEOUT_SECONDS)  # type: ignore[misc]
def get_loc_stats(url: HttpUrl, branch: str | None = None) -> tuple[TotalByLanguageDict, Total]:
    with TemporaryDirectory(prefix="tmp_", dir=".") as tmpdir_path:
        repo = Repo.clone_from(
            url=str(url),
            branch=branch,
            to_path=tmpdir_path,
            depth=1,
            single_branch=True,
            kill_after_timeout=__TIMEOUT_SECONDS,
        )
        langs = Languages()
        langs.get_statistics(paths=[str(repo.working_dir)], ignored=[], config=Config())
    result = TotalByLanguageDict.model_validate(
        dict(
            sorted(
                langs.report_compact_plain().items(),
                key=lambda item: -item[1]["lines"],
            ),
        ),
    )
    total = Total.model_validate(langs.total_plain())
    return result, total


def get_loc_svg(result: TotalByLanguageDict) -> bytes:
    bar_chart = HorizontalBar(
        inner_radius=0.4,
        title="LOC by language",
    )
    result_dict = result.model_dump()
    loc_by_lang = {lang: loc for lang, total in result_dict.items() if (loc := int(total["code"])) > 0}
    for language, loc in sorted(loc_by_lang.items(), key=lambda i: i[1], reverse=True):
        bar_chart.add(language, loc)
    return bytes(bar_chart.render())

"""Server for locloc."""

import importlib.resources
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from git.exc import GitCommandError
from pydantic import HttpUrl
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.templating import _TemplateResponse
from timeout_decorator import (  # type: ignore[import-not-found]
    TimeoutError as TDTimeoutError,
)

from . import __version__
from .loc import get_loc_stats, get_loc_svg

resource_root_path = Path(str(importlib.resources.files("locloc")))
limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=True,
)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
templates = Jinja2Templates(directory=resource_root_path / "templates")

app.mount("/static", StaticFiles(directory=resource_root_path / "static_files"))


@app.api_route(
    "/healthcheck",
    methods=["GET", "HEAD"],
    status_code=status.HTTP_200_OK,
)
def healthcheck() -> Response:
    """Healthcheck endpoint."""
    return Response(content="OK", media_type="text/plain")


@app.api_route("/res", methods=["GET", "HEAD"], response_class=HTMLResponse)
@limiter.limit("6/minute")
async def res(
    request: Request,  # noqa: ARG001
    url: Annotated[HttpUrl, Query(max_length=255)],
    *,
    branch: Annotated[str | None, Query(max_length=255)] = None,
    is_svg: bool = False,
) -> JSONResponse:
    """Get lines of code statistics for a given repository.

    Args:
        request (Request): The request object.
        url (HttpUrl): The URL of the repository.
        branch (Optional[str]): The branch to analyze. If None, the default branch will be used.
        is_svg (bool): Whether to return SVG data.

    Returns:
        JSONResponse: A JSON response containing the lines of code statistics.

    Raises:
        HTTPException: If there is an error with the git command or if the operation times out.
    """
    try:
        result, total = get_loc_stats(
            url,
            branch if branch is not None and branch != "" else None,
        )
        svg = get_loc_svg(result) if is_svg else None
    except GitCommandError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from None
    except TDTimeoutError:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT) from None
    return JSONResponse(
        content={
            "result": jsonable_encoder(result),
            "total": jsonable_encoder(total),
            "svg": jsonable_encoder(svg),
        },
    )


@app.api_route("/svg", methods=["GET", "HEAD"], response_class=HTMLResponse)
@limiter.limit("6/minute")
async def svg(
    request: Request,  # noqa: ARG001
    url: Annotated[HttpUrl, Query(max_length=255)],
    *,
    branch: Annotated[str | None, Query(max_length=255)] = None,
) -> Response:
    """Get SVG representation of lines of code statistics for a given repository.

    Args:
        request (Request): The request object.
        url (HttpUrl): The URL of the repository.
        branch (Optional[str]): The branch to analyze. If None, the default branch will be used.

    Returns:
        Response: A response containing the SVG representation of the lines of code statistics.

    Raises:
        HTTPException: If there is an error with the git command or if the operation times out.
    """
    try:
        result, _total = get_loc_stats(
            url,
            branch if branch is not None and branch != "" else None,
        )
        svg = get_loc_svg(result)
    except GitCommandError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from None
    except TimeoutError:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT) from None
    expiry_time = datetime.now(tz=UTC) + timedelta(3666)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "max-age=3666,s-maxage=3666,no-store,proxy-revalidate",
            "Expires": expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Pragma": "no-cache",
        },
    )


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def root(request: Request) -> _TemplateResponse:
    """Root endpoint that serves the main page.

    Args:
        request (Request): The request object.

    Returns:
        _TemplateResponse: A template response containing the main page.
    """
    return templates.TemplateResponse(
        "index.j2",
        {"request": request, "version": __version__},
    )


def main() -> None:
    """Main function to run the FastAPI server."""
    config = uvicorn.Config(
        app,
        port=5000,
        log_level="info",
        reload=bool(os.environ.get("DEBUG")),
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()

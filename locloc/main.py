from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from . import __version__

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# @app.get("/")
# async def root():


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("index.html", {"request": request, "version": __version__})


def main() -> None:
    config = uvicorn.Config(app, port=5000, log_level="info")
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()

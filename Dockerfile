FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY . /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
ENTRYPOINT ["uv", "run", "python", "-m", "uvicorn", "locloc.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM python:3.14-slim@sha256:656d12e70054d5fda18a045e2494c96701e9792dd1445f95b3d038df954f57e9
COPY --from=ghcr.io/astral-sh/uv:latest@sha256:d1cbaeadc234fe19c0d93daabcf5e98738cd93c6d1dd4918ef6aa30735feb23a /uv /bin/uv

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY . /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN uv sync --locked --no-dev

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
ENTRYPOINT ["uv", "run", "python", "-m", "uvicorn", "locloc.main:app", "--host", "0.0.0.0", "--port", "8080"]

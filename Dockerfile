FROM python:3

ARG VERSION
ENV VERSION ${VERSION:-master}

RUN python -m pip --no-cache-dir install git+https://github.com/eggplants/locloc@${VERSION}

EXPOSE 8080
ENTRYPOINT ["python", "-m", "uvicorn", "locloc.main:app", "--host", "0.0.0.0", "--port", "8080"]

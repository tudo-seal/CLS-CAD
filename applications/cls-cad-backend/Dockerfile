FROM pypy:3.10-slim as just-python

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache


FROM just-python as with-poetry

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

FROM just-python as cls-cad

COPY --from=with-poetry ${POETRY_VENV} ${POETRY_VENV}
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /cls_cad_backend
COPY poetry.lock pyproject.toml ./
RUN apt-get update && apt-get install -y libxft2 libxext6 git gcc \
    && poetry install --with docker --no-interaction --no-cache --no-ansi --without dev\
    && apt-get purge -y --auto-remove git gcc\
    && rm -rf /var/lib/apt/lists/*
COPY . /cls_cad_backend
RUN touch cls_cad_backend/database/container


ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN poetry install --with docker --no-interaction --no-cache --no-ansi --without dev
EXPOSE 8000
CMD ["poetry", "run", "docker"]

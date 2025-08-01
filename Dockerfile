FROM python:3.12

EXPOSE 80

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./.python-version ./.python-version

COPY ./pyproject.toml ./pyproject.toml

COPY ./uv.lock ./uv.lock

RUN uv sync --no-group dev --frozen --no-cache

COPY ./Makefile /code/Makefile

COPY ./logging /code/logging

COPY ./src /code/src

CMD ["make", "run-prod"]


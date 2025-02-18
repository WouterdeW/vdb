FROM python:3.10-slim

ARG YOUR_ENV

ENV YOUR_ENV=${YOUR_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  # Poetry's configuration:
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  POETRY_HOME='/usr/local' \
  POETRY_VERSION=2.0.1

# System deps:
RUN pip install poetry

# Copy only requirements to cache them in docker layer
WORKDIR /opt/dagster/app

COPY poetry.lock pyproject.toml /opt/dagster/app

# Project initialization:
RUN poetry install --no-root

# Creating folders, and files for a project:
COPY vandebron/. /opt/dagster/app

EXPOSE 4000

CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "4000","-f","knmi_edr_scraper.py"]
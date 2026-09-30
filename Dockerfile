FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="CNPJ Lakehouse"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:/usr/local/bin:$PATH

RUN pip install --no-cache-dir uv==0.8.17
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY cnpj_lakehouse ./cnpj_lakehouse
COPY dbt ./dbt
COPY scripts ./scripts
RUN uv sync --locked
RUN useradd --create-home --uid 10001 lakehouse && mkdir -p /runtime /prefect /home/lakehouse/.prefect && chown -R lakehouse:lakehouse /app /runtime /prefect /home/lakehouse/.prefect
USER lakehouse
ENV CNPJ_LAKEHOUSE_RUNTIME_ROOT=/runtime PREFECT_HOME=/prefect PREFECT_API_URL=http://prefect-server:4200/api PREFECT_UI_API_URL=/api
EXPOSE 4200 8501

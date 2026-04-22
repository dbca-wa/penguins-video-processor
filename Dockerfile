FROM python:3.13
LABEL org.opencontainers.image.authors=asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source=https://github.com/dbca-wa/penguins-video-processor

RUN apt-get update -y \
  && apt install -y handbrake-cli \
  && rm -rf /var/lib/apt/lists/*

# Copy and configure uv, to install dependencies
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --link-mode=copy --compile-bytecode --no-python-downloads --frozen

COPY *.py ./
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "processor.py"]

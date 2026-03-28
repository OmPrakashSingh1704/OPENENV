FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# HuggingFace Spaces runs as a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first (layer-cached)
# uv is ~10-100x faster than pip
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy source
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

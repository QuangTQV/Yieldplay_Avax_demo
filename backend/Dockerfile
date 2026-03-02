FROM python:3.12-slim

# Cài curl để cài uv
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Cài uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy file dependency trước để cache layer tốt hơn
COPY pyproject.toml uv.lock* ./

# Cài dependencies bằng uv
RUN uv sync --no-dev

# Copy source code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
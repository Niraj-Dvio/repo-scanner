FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    gnupg \
    nodejs \
    npm \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt

# Upgrade pip and install wheels first to prefer binary packages
RUN python -m pip install --upgrade pip setuptools wheel

# Prefer binary wheels where possible; having system libs installed helps build any native deps
RUN pip install --no-cache-dir --prefer-binary -r /app/requirements.txt

# Install semgrep (pip) and snyk (npm global) so code quality tools are available
RUN python -m pip install --no-cache-dir semgrep || true
RUN npm install -g snyk || true

# Copy backend source
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV UVICORN_RELOAD=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

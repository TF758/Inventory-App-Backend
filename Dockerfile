FROM python:3.12-trixie

# Prevent Python from writing .pyc files and ensure logs are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency file first for caching
COPY requirements.txt .

# Install dependencies (system environment)
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
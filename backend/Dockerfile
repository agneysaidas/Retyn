FROM python:3.11-slim

WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m appuser
USER appuser

# Copy project
COPY . .

# Collect static (optional but recommended later)
# RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "retyn.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
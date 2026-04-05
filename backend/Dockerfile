FROM python:3.11-slim

WORKDIR /app

#System deps
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

#Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#COPY Project
COPY . .

#Collect static(optional now)
# RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "retyn.wsgi:application", "--bind", "0.0.0.0:8000"]
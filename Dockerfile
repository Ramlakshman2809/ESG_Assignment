FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and seed data
RUN python manage.py migrate
RUN python manage.py seed_data

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "esg_backend.wsgi"]
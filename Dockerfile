# Use the official Python image as a base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . /app/

# Ensure static directory exists before collecting static files
RUN mkdir -p /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Apply migrations before running the server
RUN python manage.py migrate

# Expose the port the app runs on
EXPOSE 8000

# Start Gunicorn server with logging and worker configuration
CMD ["gunicorn", "Portfolio.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=3", "--timeout", "120"]

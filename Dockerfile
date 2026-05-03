FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Install dependencies
COPY pyproject.toml requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Copy project code
COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start command (1 worker to save memory for ML model)
CMD ["gunicorn", "movieflix.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1"]

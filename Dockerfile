FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/

# HTTP API + UDP mesh port
EXPOSE 8000 9999/udp

# Production: set SHILL_ROOT_PASSWORD, SHILL_TOTP_SECRET, SHILL_MESH_PSK,
# SHILL_VAULT_PASSPHRASE (see .env.example). Dev fallback generates random creds.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

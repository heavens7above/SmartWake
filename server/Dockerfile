# Base container locking standard Linux features and lightweight Python.
FROM python:3.11-slim-bullseye

# Prevent python from producing disk-consuming compiled byte-codes
ENV PYTHONDONTWRITEBYTECODE=1
# Force unbuffered IO streams immediately targeting stdout so Railway parses logs natively
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Ensure base runtime tools (Scikit-learn requires compiled C bindings, so ensure gcc or related libs exist if missing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies distinctly
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Securely copy source application 
COPY . .

# Expose standard 8000
EXPOSE 8000

# Mount standard Uvicorn worker directly to Railway ENV PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

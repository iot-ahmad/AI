FROM python:3.11-slim

# Install system deps: FFmpeg + Arabic/Unicode fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-nakula \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render/Railway set PORT automatically
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

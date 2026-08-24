FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch and matching TorchAudio
RUN pip install --no-cache-dir \
    torch==2.11.0 \
    torchaudio==2.11.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Application code and runtime dependencies
COPY app ./app
COPY agent ./agent
COPY audio_features ./audio_features
COPY assets ./assets
COPY data ./data
COPY schemas ./schemas
COPY vosk_models ./vosk_models
COPY retraining ./retraining
COPY simulator ./simulator
COPY word_level ./word_level

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.13-slim-bookworm

WORKDIR /app

# PyAudio のビルドに必要（strands-agents[bidi] の依存）
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py config.py ./
COPY tools/ ./tools/

EXPOSE 8080

CMD ["opentelemetry-instrument", "python", "agent.py"]

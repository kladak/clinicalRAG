FROM python:3.11-slim
WORKDIR /app
ENV ANONYMIZED_TELEMETRY=False \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake the ONNX MiniLM weights into the image so process start needs no network.
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()(['warmup'])"
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

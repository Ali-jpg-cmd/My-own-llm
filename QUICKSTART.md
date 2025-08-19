# Quick Start Guide (100% Free Local)

## Prerequisites
- Python 3.11+
- Enough disk for a small GGUF (~0.7 GB)
- No GPU required (CPU-only works)

## 1) Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

## 2) Get a GGUF model
```bash
# Download TinyLlama GGUF (~0.7 GB)
python ../scripts/download_gguf.py
# Result: ./models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf
```

## 3) Configure (optional)
```bash
cp env.example .env
# Ensure:
# LLM_PROVIDER=llamacpp
# LLM_MODEL_PATH=models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf
```

## 4) Run the API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5) Try it out
```bash
python ../test_api.py
```

## Docker (optional)
```bash
docker-compose up -d --build
```
This mounts `./models` so your GGUF is available at `/app/models` in the container.

## Notes
- For larger models, update `LLM_MODEL_PATH` and ensure enough RAM.
- Everything runs locally (SQLite + llama.cpp + in-memory rate limits). No keys required.

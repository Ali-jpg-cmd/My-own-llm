# My Own LLM API

A 100% free, local AI API powered by llama.cpp (GGUF), FastAPI, and SQLite. No cloud keys or paid services required.

## 🚀 Features

- **Local LLM**: Run GGUF models (e.g., TinyLlama) via llama.cpp
- **Zero Cost**: SQLite + in-memory rate limits + local inference
- **Secure**: API keys (hashed), JWT-ready
- **Analytics**: Usage tracking in SQLite
- **Docker**: One-service compose

## 🛠️ Quick Start (Free Local)

1. Create a Python venv and install deps:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Download a small GGUF model:
   ```bash
   python ../scripts/download_gguf.py
   # or manually place a GGUF into ./models and set LLM_MODEL_PATH
   ```

3. Configure env (optional; defaults already free):
   ```bash
   cp env.example .env
   # Ensure LLM_PROVIDER=llamacpp and LLM_MODEL_PATH points to your GGUF
   ```

4. Run the API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. Test endpoints:
   ```bash
   python ../test_api.py
   ```

## 🐳 Docker (CPU-only, free)

```bash
# Build and run just the API (SQLite + local models)
docker-compose up -d --build
```
Models directory `./models` is mounted to `/app/models` in the container.

## 🔑 Auth & Rate Limits

- API keys issued on register/login; stored hashed
- In-memory rate limiting (per process) by default

## 🔧 Config

See `backend/env.example`. Key vars:
- `DATABASE_URL=sqlite:///./llm_api.db`
- `LLM_PROVIDER=llamacpp`
- `LLM_MODEL_PATH=models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf`
- `RATE_LIMIT_REQUESTS=100`

## 📚 Docs
- Model selection: `docs/step1-model-selection.md` (HF/OpenAI optional; not required for free stack)
- AWS/GCP deployment remain available but not needed for free setup

## License
MIT

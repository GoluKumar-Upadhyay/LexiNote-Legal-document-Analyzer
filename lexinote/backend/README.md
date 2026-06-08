# LexiNote Backend

FastAPI backend for LexiNote with a single-service architecture.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Create `.env` from `.env.example` and add your provider keys.

Recommended provider order right now:

```env
LLM_PROVIDER_PRIORITY=gemini,xai,openrouter,groq,heuristic
```

import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Parallel LLM processing models (run simultaneously)
PARALLEL_MODELS = [m.strip() for m in os.getenv(
    "PARALLEL_MODELS",
    # Multiple models for diverse analysis (run in parallel)
    "google/gemini-2.5-pro,x-ai/grok-2,deepseek/deepseek-r1,meta-llama/llama-3.1-8b-instruct"
).split(",") if m.strip()]

# High-quality synthesis model (combines parallel results)
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "openai/gpt-5-chat")

# Keep old names for backward compatibility
CASCADE_MODELS = PARALLEL_MODELS
FINALIZER_MODEL = SYNTHESIS_MODEL

PARALLEL_TIMEOUT_MS = int(os.getenv("PARALLEL_TIMEOUT_MS", "8000"))
CASCADE_MIN_CHARS = int(os.getenv("CASCADE_MIN_CHARS", "200"))
CHAT_HISTORY_MAX = int(os.getenv("CHAT_HISTORY_MAX", "20"))
FREE_ANALYZE_LIMIT = int(os.getenv("FREE_ANALYZE_LIMIT", "1"))

HEALTH_MODE = os.getenv("HEALTH_MODE", "strict")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

LOG_PROVIDER_RAW = os.getenv("LOG_PROVIDER_RAW", "true").lower() == "true"
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "365"))

# Safety and rate limits
PRESCRIPTION_BLOCK = os.getenv("PRESCRIPTION_BLOCK", "true").lower() == "true"
DAILY_CHAT_LIMIT = int(os.getenv("DAILY_CHAT_LIMIT", "100"))

# Health moderation via LLM (optional, used when HEALTH_MODE=hybrid)
MODERATION_MODEL = os.getenv("MODERATION_MODEL", "meta-llama/llama-3.1-8b-instruct")
MODERATION_TIMEOUT_MS = int(os.getenv("MODERATION_TIMEOUT_MS", "2000"))

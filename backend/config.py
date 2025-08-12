import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Parallel LLM processing models (run simultaneously)
PARALLEL_MODELS = [m.strip() for m in os.getenv(
    "PARALLEL_MODELS",
    # New web search enabled models (run in parallel)
    "openai/gpt-4o:online,google/gemini-2.5-pro:online,x-ai/grok-4:online,anthropic/claude-sonnet-4:online"
).split(",") if m.strip()]

# High-quality synthesis model (combines parallel results)
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "openai/gpt-5-chat:online")

# Keep old names for backward compatibility
CASCADE_MODELS = PARALLEL_MODELS
FINALIZER_MODEL = SYNTHESIS_MODEL

# OLD MODELS (commented out for backup)
# PARALLEL_MODELS = [m.strip() for m in os.getenv(
#     "PARALLEL_MODELS",
#     # Multiple models for diverse analysis (run in parallel)
#     "google/gemini-2.5-pro,x-ai/grok-2,deepseek/deepseek-r1,meta-llama/llama-3.1-8b-instruct"
# ).split(",") if m.strip()]
# SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "openai/gpt-5-chat")

PARALLEL_TIMEOUT_MS = int(os.getenv("PARALLEL_TIMEOUT_MS", "8000"))
# Backward compatibility
CASCADE_TIMEOUT_MS = PARALLEL_TIMEOUT_MS
CASCADE_MIN_CHARS = int(os.getenv("CASCADE_MIN_CHARS", "200"))
CHAT_HISTORY_MAX = int(os.getenv("CHAT_HISTORY_MAX", "20"))
FREE_ANALYZE_LIMIT = int(os.getenv("FREE_ANALYZE_LIMIT", "1"))

HEALTH_MODE = os.getenv("HEALTH_MODE", "topic")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

LOG_PROVIDER_RAW = os.getenv("LOG_PROVIDER_RAW", "true").lower() == "true"
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "365"))

# Safety and rate limits
PRESCRIPTION_BLOCK = os.getenv("PRESCRIPTION_BLOCK", "true").lower() == "true"
DAILY_CHAT_LIMIT = int(os.getenv("DAILY_CHAT_LIMIT", "100"))

# Health moderation via LLM (stable, fast model for topic classification)
MODERATION_MODEL = os.getenv("MODERATION_MODEL", "google/gemini-2.5-flash")
MODERATION_TIMEOUT_MS = int(os.getenv("MODERATION_TIMEOUT_MS", "3000"))

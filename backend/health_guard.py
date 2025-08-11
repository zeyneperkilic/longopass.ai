from typing import Tuple
import re
import difflib
import time
import hashlib
from .config import PRESCRIPTION_BLOCK, HEALTH_MODE, MODERATION_MODEL, MODERATION_TIMEOUT_MS
from .openrouter_client import call_chat_model

ALLOW_KEYWORDS = [
    "sağlık", "beslenme", "supplement", "vitamin", "mineral", "diyet", "uyku",
    "egzersiz", "kan", "laboratuvar", "test", "kolesterol", "hbA1c", "glukoz",
    "magnesium", "omega", "d3", "b12", "demir", "tiroid", "tansiyon", "insülin",
    "diabet", "kalp", "karaciğer", "böbrek", "semptom", "belirti"
]
DENY_KEYWORDS = [
    "kripto", "borsa", "hisse", "hukuk", "bahis", "hack", "nsfw", "futbol",
    "siyaset", "politika", "vergi", "emlak"
]

def _normalize(t: str) -> str:
    t = (t or "").lower()
    return (t.replace("ı", "i").replace("ö", "o").replace("ü", "u")
             .replace("ş", "s").replace("ğ", "g").replace("ç", "c"))

def _fuzzy_any(text: str, candidates: list[str], threshold: float = 0.82) -> bool:
    # token-level fuzzy match using difflib (std lib)
    tokens = re.findall(r"[a-z0-9]+", text)
    for cand in candidates:
        c = _normalize(cand)
        for tok in tokens:
            if difflib.SequenceMatcher(None, tok, c).ratio() >= threshold:
                return True
    return False

def is_health_topic(text: str) -> bool:
    t = _normalize(text)
    if any(k in t for k in DENY_KEYWORDS):
        return False
    if any(k in t for k in ALLOW_KEYWORDS) or _fuzzy_any(t, ALLOW_KEYWORDS):
        return True
    # widen health detection with lab/organ/symptom patterns
    lab_units = r"\b(mg\/dl|mmol\/l|mui\/ml|miu\/l|ng\/ml|ug\/l|iu|ml)\b"
    labs = r"\b(hdl|ldl|hba1c|tsh|crp|trigliserid|triglyceride|kolesterol|ferritin|b12|d vitamini|vit d)\b"
    organs = r"\b(karaciger|bobrek|tiroid|kalp|akciger)\b"
    symptoms = r"\b(ates|oksuruk|bas agrisi|mide bulantisi|ishal|agrisi|agrim var|agriyor|nabiz|tansiyon|iyi hissetmiyorum|kotu hissediyorum|halsizim|yorgunum|rahatsizim|hasta hissediyorum)\b"
    if re.search(lab_units, t) and re.search(labs, t):
        return True
    if re.search(organs, t) or re.search(symptoms, t):
        return True
    # lenient mode: allow if not explicitly denied
    if (HEALTH_MODE or "").lower() == "lenient":
        return True
    return False

def is_prescription_like(text: str) -> bool:
    if not PRESCRIPTION_BLOCK:
        return False
    t = (text or "").lower()
    t = (t
         .replace("ı", "i").replace("ö", "o").replace("ü", "u")
         .replace("ş", "s").replace("ğ", "g").replace("ç", "c"))
    dose = r"\b\d+(\.\d+)?\s?(mg|mcg|ug|g|iu|ml|mg\/dl|mmol\/l)\b"
    freq = r"(gunde\s?\d+|her\s?\d+\s?(saat|gun)|\b[1-4]x\b)"
    verbs = ["doz", "dozu", "kac mg", "recete", "yaz", "ilac", "antibiyotik", "antidepresan", "agri kesici"]
    if re.search(dose, t) and re.search(freq, t):
        return True
    if any(v in t for v in verbs):
        return True
    return False

def guard_or_message(text: str) -> Tuple[bool, str]:
    if is_prescription_like(text):
        return False, "İlaç/doz yazamıyorum veya reçete düzenleyemem. Uygun tedavi için hekiminize danışın."

    mode = (HEALTH_MODE or "").lower()

    # Topic-first: use a lightweight LLM classifier
    if mode == "topic":
        label = classify_topic_llm(text)
        if label in ("HEALTH", "AMBIGUOUS"):
            return True, ""
        if label == "MEDICAL_PROHIBITED":
            return False, "İlaç/doz/teşhis talebi gerçekleştiremiyorum. Uygun tedavi için hekiminize danışın."
        return False, "Üzgünüm, Longopass AI yalnızca sağlık ve supplement konularında yardımcı olabilir."

    # Strict keyword/regex first
    if is_health_topic(text):
        return True, ""

    # Hybrid: fallback to LLM if rules inconclusive, then to keyword-based check
    if mode == "hybrid":
        try:
            label = classify_topic_llm(text)
            if label in ("HEALTH", "AMBIGUOUS"):
                return True, ""
            elif label == "NON_HEALTH":
                return False, "Üzgünüm, Longopass AI yalnızca sağlık ve supplement konularında yardımcı olabilir."
        except Exception:
            # LLM failed, fallback to keyword-based check
            if is_health_topic_keyword_based(text):
                return True, ""
    
    return False, "Üzgünüm, Longopass AI yalnızca sağlık ve supplement konularında yardımcı olabilir."


# ---------- Topic classifier (LLM) with small TTL cache ----------
_TOPIC_CACHE_TTL_S = 1800  # 30 minutes
_topic_cache: dict[str, tuple[str, float]] = {}

def _cache_key(text: str) -> str:
    t = _normalize(text)
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def _cache_get(k: str) -> str | None:
    now = time.time()
    item = _topic_cache.get(k)
    if not item:
        return None
    label, exp = item
    if now > exp:
        _topic_cache.pop(k, None)
        return None
    return label

def _cache_set(k: str, label: str):
    _topic_cache[k] = (label, time.time() + _TOPIC_CACHE_TTL_S)

def classify_topic_llm(text: str) -> str:
    """Return one of: HEALTH | NON_HEALTH | MEDICAL_PROHIBITED | AMBIGUOUS"""
    key = _cache_key(text)
    cached = _cache_get(key)
    if cached:
        return cached
    sys = (
        "Sınıflandırma yap. YALNIZCA bu etiketlerden birini döndür: "
        "HEALTH, NON_HEALTH, MEDICAL_PROHIBITED, AMBIGUOUS. Açıklama ekleme."
    )
    usr = (
        "Metin: " + str(text) + "\n\n" +
        "Kriter: Sağlık/supplement/laboratuvar/symptom bağlamı varsa HEALTH. "
        "İlaç/doz/teşhis talebi ise MEDICAL_PROHIBITED. Belirsizse AMBIGUOUS. Aksi NON_HEALTH."
    )
    out = call_chat_model(MODERATION_MODEL,
                          [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                          temperature=0.0, max_tokens=3)
    label = (out.get("content") or "").strip().upper()
    # normalize to known set
    if "MEDICAL" in label:
        label = "MEDICAL_PROHIBITED"
    elif label.startswith("HEALTH"):
        label = "HEALTH"
    elif label.startswith("NON"):
        label = "NON_HEALTH"
    elif label.startswith("AMBIG"):
        label = "AMBIGUOUS"
    else:
        label = "AMBIGUOUS"
    _cache_set(key, label)
    return label

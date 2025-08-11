import json
from typing import Tuple
from .config import CASCADE_MIN_CHARS
from .health_guard import is_health_topic

def parse_json_safe(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None

def is_valid_chat(text: str) -> bool:
    if not text or len(text.strip()) < CASCADE_MIN_CHARS:
        return False
    if not is_health_topic(text):
        return False
    return True

def is_valid_analyze(text: str) -> Tuple[bool, str]:
    # Expect strict JSON with keys
    data = parse_json_safe(text)
    if not isinstance(data, dict):
        return False, "JSON değil"
    if "recommendations" not in data:
        return False, "recommendations yok"
    if not isinstance(data["recommendations"], list):
        return False, "recommendations liste değil"
    # optional analysis dict
    return True, ""

from typing import List, Dict, Any
from .config import CASCADE_MODELS, FINALIZER_MODEL
from .openrouter_client import call_chat_model
from .utils import is_valid_chat, is_valid_analyze, parse_json_safe

SYSTEM_HEALTH = ("Sen Longopass AI'sın. SADECE sağlık/supplement/laboratuvar konularında yanıt ver. "
                 "Off-topic'te kibarca reddet. Yanıtlar bilgilendirme amaçlıdır; tanı/tedavi için hekim gerekir.")

def cascade_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    # messages already includes system + history + user
    for model in CASCADE_MODELS:
        res = call_chat_model(model, messages, temperature=0.6, max_tokens=600)
        if not is_valid_chat(res["content"]):
            continue
        res["model_used"] = model
        return res
    # if none acceptable, return last model name with empty content
    return {"content": "", "model_used": CASCADE_MODELS[-1]}

def finalize_text(text: str) -> str:
    final_messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_HEALTH +
                " Görevin: Aşağıdaki asistan yanıtını kalite (doğruluk, tutarlılık, fayda, güvenlik) açısından değerlendir;"
                " YETERSİZ/HATALI ise baştan, doğru ve güvenli bir yanıt olarak YENİDEN YAZ. Gerekirse eksikleri tamamla, yanlışları düzelt."
                " Gereksiz tekrarları çıkar. Net, anlaşılır Türkçe kullan; mümkün olduğunda kısa madde işaretleriyle ver."
                " Off-topic istekleri kibarca reddet. Sadece nihai yanıtı döndür."
            ),
        },
        {"role": "user", "content": text},
    ]
    final = call_chat_model(FINALIZER_MODEL, final_messages, temperature=0.2, max_tokens=800)
    return final["content"]

def build_analyze_prompt(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    schema = (
        "STRICT JSON ŞEMASI:\n"
        "{\n"
        '  "recommendations": [\n'
        '    {"id": "string|optional", "name": "string", "reason": "string", "source": "consensus"}\n'
        "  ],\n"
        '  "analysis": {"...": "..."}\n'
        "}\n"
        "Sadece bu JSON'u üret, açıklama yazma."
    )
    user = f"Kullanıcı verisi (quiz/lab): {payload}"
    return [
        {"role": "system", "content": SYSTEM_HEALTH + " Sadece sağlığa odaklan ve kesinlikle STRICT JSON üret."},
        {"role": "user", "content": user + "\n\n" + schema}
    ]

def cascade_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    messages = build_analyze_prompt(payload)
    last = None
    for model in CASCADE_MODELS:
        res = call_chat_model(model, messages, temperature=0.3, max_tokens=900)
        last = res
        ok, _ = is_valid_analyze(res["content"])
        if ok:
            res["model_used"] = model
            return res
    last["model_used"] = CASCADE_MODELS[-1]
    return last

def finalize_analyze(json_text: str) -> str:
    # Keep JSON shape; dedupe/order; no new items
    messages = [
        {"role": "system", "content": SYSTEM_HEALTH + " Bu JSON'u yalnızca tekilleştir, önem sırasına koy ve geçerli JSON olarak geri ver. Yeni öğe ekleme."},
        {"role": "user", "content": json_text}
    ]
    final = call_chat_model(FINALIZER_MODEL, messages, temperature=0.0, max_tokens=900)
    return final["content"]

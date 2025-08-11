from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import PARALLEL_MODELS, SYNTHESIS_MODEL, CASCADE_MODELS, FINALIZER_MODEL
from .openrouter_client import call_chat_model
from .utils import is_valid_chat, is_valid_analyze, parse_json_safe

SYSTEM_HEALTH = ("Sen Longopass AI'sın. SADECE sağlık/supplement/laboratuvar konularında yanıt ver. "
                 "Off-topic'te kibarca reddet. Yanıtlar bilgilendirme amaçlıdır; tanı/tedavi için hekim gerekir.")

def cascade_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    # messages already includes system + history + user
    for model in PARALLEL_MODELS:
        res = call_chat_model(model, messages, temperature=0.6, max_tokens=600)
        if not is_valid_chat(res["content"]):
            continue
        res["model_used"] = model
        return res
    # if none acceptable, return last model name with empty content
    return {"content": "", "model_used": PARALLEL_MODELS[-1]}

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
    final = call_chat_model(SYNTHESIS_MODEL, final_messages, temperature=0.2, max_tokens=800)
    return final["content"]

def build_analyze_prompt(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    schema = (
        "STRICT JSON ŞEMASI ve ÖRNEK:\n"
        "{\n"
        '  "recommendations": [\n'
        '    {"name": "D Vitamini", "reason": "Eksiklik belirtileri mevcut", "source": "consensus"},\n'
        '    {"name": "Magnezyum", "reason": "Yorgunluk ve kas krampları için", "source": "consensus"}\n'
        "  ],\n"
        '  "analysis": {\n'
        '    "summary": "D vitamini eksikliği olası, takviye önerilir",\n'
        '    "key_findings": ["Yorgunluk", "Saç dökülmesi"],\n'
        '    "risk_level": "düşük"\n'
        "  }\n"
        "}\n"
        "SADECE VE SADECE bu JSON formatında yanıt ver. Hiçbir açıklama, metin ekleme. "
        "recommendations dizi boş olabilir ama analysis dolu olmalı."
    )
    user = f"Kullanıcı verisi: {payload}"
    return [
        {"role": "system", "content": SYSTEM_HEALTH + " Sen bir sağlık supplement uzmanısın. Kullanıcı verilerini analiz et ve supplement önerileri yap. SADECE JSON döndür."},
        {"role": "user", "content": user + "\n\n" + schema}
    ]

def build_synthesis_prompt(responses: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Build prompt for GPT-5 to synthesize multiple model responses"""
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir synthesis uzmanısın. "
        "Birden fazla AI modelin verdiği analiz sonuçlarını inceleyip, "
        "en doğru, tutarlı ve faydalı bir FINAL sonuç üret. "
        "\n\nKurallar:"
        "\n1. SADECE JSON formatında yanıt ver"
        "\n2. En tutarlı önerileri birleştir"
        "\n3. Çelişkili önerilerde en mantıklı olanı seç"
        "\n4. Analysis kısmını en kapsamlı şekilde yaz"
        "\n5. Risk level'ı en doğru şekilde değerlendir"
        "\n6. Tekrarlayan önerileri birleştir"
    )
    
    # Format all responses for comparison
    responses_text = "\n\n=== MODEL RESPONSES ===\n"
    for i, resp in enumerate(responses, 1):
        responses_text += f"\nMODEL {i} ({resp['model']}):\n{resp['response']}\n"
    
    responses_text += "\n=== SYNTHESIS GÖREV ===\n"
    responses_text += (
        "Yukarıdaki tüm model yanıtlarını analiz et ve tek bir tutarlı JSON oluştur. "
        "En iyi önerileri birleştir, analysis'i geliştir, risk değerlendirmesini optimize et."
    )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": responses_text}
    ]

def parallel_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run multiple LLMs in parallel, then synthesize results with GPT-5"""
    try:
        messages = build_analyze_prompt(payload)
        
        # Step 1: Call multiple models in parallel
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            # Submit all model calls simultaneously
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.3, 1200): model 
                for model in PARALLEL_MODELS
            }
            
            # Collect valid responses
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    ok, _ = is_valid_analyze(result["content"])
                    if ok:
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Model {model} failed: {e}")
                    continue
        
        # Step 2: If no valid responses, fallback to single model
        if not responses:
            print("All parallel models failed, falling back to single model")
            return cascade_analyze_fallback(payload)
        
        # Step 3: Synthesize with GPT-5
        synthesis_prompt = build_synthesis_prompt(responses)
        final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.1, max_tokens=1500)
        
        final_result["models_used"] = [r["model"] for r in responses]
        final_result["synthesis_model"] = SYNTHESIS_MODEL
        return final_result
        
    except Exception as e:
        print(f"Parallel analyze failed: {e}, falling back to sequential")
        return cascade_analyze_fallback(payload)

def cascade_analyze_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback to sequential cascade if parallel fails"""
    messages = build_analyze_prompt(payload)
    last = None
    for model in PARALLEL_MODELS:
        res = call_chat_model(model, messages, temperature=0.3, max_tokens=1200)
        last = res
        ok, _ = is_valid_analyze(res["content"])
        if ok:
            res["model_used"] = model
            return res
    last["model_used"] = PARALLEL_MODELS[-1]
    return last

# Keep old function for backward compatibility
def cascade_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    return parallel_analyze(payload)

def finalize_analyze(json_text: str) -> str:
    # Keep JSON shape; dedupe/order; no new items
    messages = [
        {"role": "system", "content": SYSTEM_HEALTH + " Bu JSON'u yalnızca tekilleştir, önem sırasına koy ve geçerli JSON olarak geri ver. Yeni öğe ekleme."},
        {"role": "user", "content": json_text}
    ]
    final = call_chat_model(SYNTHESIS_MODEL, messages, temperature=0.0, max_tokens=900)
    return final["content"]

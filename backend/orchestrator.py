from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import PARALLEL_MODELS, SYNTHESIS_MODEL, CASCADE_MODELS, FINALIZER_MODEL
from .openrouter_client import call_chat_model
from .utils import is_valid_chat, is_valid_analyze, parse_json_safe

SYSTEM_HEALTH = ("Sen Longopass AI'sın. SADECE sağlık/supplement/laboratuvar konularında yanıt ver. "
                 "Off-topic'te kibarca reddet. Yanıtlar bilgilendirme amaçlıdır; tanı/tedavi için hekim gerekir.")

def parallel_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Run parallel chat with multiple models, then synthesize with GPT-5"""
    try:
        # Step 1: Call multiple models in parallel
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.6, 600): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if is_valid_chat(result["content"]):
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Chat model {model} failed: {e}")
                    continue
        
        # Step 2: If no valid responses, fallback
        if not responses:
            print("All chat models failed, fallback to single model")
            return cascade_chat_fallback(messages)
        
        # Step 3: If only one response, return it directly
        if len(responses) == 1:
            return {
                "content": responses[0]["response"],
                "model_used": responses[0]["model"]
            }
        
        # Step 4: Synthesize multiple responses with GPT-5
        synthesis_prompt = build_chat_synthesis_prompt(responses, messages[-1]["content"])
        final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.3, max_tokens=800)
        
        final_result["models_used"] = [r["model"] for r in responses]
        final_result["synthesis_model"] = SYNTHESIS_MODEL
        return final_result
        
    except Exception as e:
        print(f"Parallel chat failed: {e}, fallback to sequential")
        return cascade_chat_fallback(messages)

def cascade_chat_fallback(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback to sequential cascade for chat"""
    for model in PARALLEL_MODELS:
        res = call_chat_model(model, messages, temperature=0.6, max_tokens=600)
        if is_valid_chat(res["content"]):
            res["model_used"] = model
            return res
    # if none acceptable, return last model name with empty content
    return {"content": "", "model_used": PARALLEL_MODELS[-1]}

def build_chat_synthesis_prompt(responses: List[Dict[str, str]], user_question: str) -> List[Dict[str, str]]:
    """Build synthesis prompt for chat responses"""
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir chat synthesis uzmanısın. "
        "Birden fazla AI modelin verdiği yanıtları inceleyip, "
        "en doğru, yararlı ve tutarlı yanıtı oluştur. "
        "\n\nKurallar:"
        "\n1. Kullanıcının sorusuna doğrudan yanıt ver"
        "\n2. Sağlık/supplement konularında en güvenli bilgiyi ver"
        "\n3. Çelişkili bilgilerde en muhafazakar yaklaşımı seç"
        "\n4. Anlaşılır ve samimi Türkçe kullan"
        "\n5. Off-topic sorularda kibarca reddet"
        "\n6. Sadece nihai yanıtı döndür, 'Model 1' gibi atıflar yapma"
    )
    
    responses_text = f"Kullanıcı sorusu: {user_question}\n\n=== MODEL RESPONSES ===\n"
    for i, resp in enumerate(responses, 1):
        responses_text += f"\nMODEL {i} ({resp['model']}):\n{resp['response']}\n"
    
    responses_text += f"\n=== SYNTHESIS GÖREV ===\n"
    responses_text += f"Yukarıdaki yanıtları analiz et ve kullanıcının sorusuna en iyi yanıtı oluştur."
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": responses_text}
    ]

# Keep old function for backward compatibility
def cascade_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return parallel_chat(messages)

def finalize_text(text: str) -> str:
    final_messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_HEALTH +
                " Sen Longopass AI'sın. Görevin: Aşağıdaki yanıtı son kontrol et ve gerekirse düzelt."
                " SADECE KULLANICIYA DOĞRUDAN CEVAP VER. Meta yorumlar (\"yanıt doğru\", \"yeniden düzenlenmiş\" vb.) YAZMA."
                " Eğer yanıt doğru ve yeterli ise, aynen gönder. Eğer hatalı/eksik ise, düzelt ve temiz yanıt ver."
                " Off-topic sorularda kibarca reddet. Net, samimi Türkçe kullan."
            ),
        },
        {"role": "user", "content": f"Bu yanıtı kontrol et ve kullanıcıya temiz şekilde sun:\n\n{text}"},
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
        "\n7. ÖNEMLI: Her öneri için 'source' alanı MUTLAKA 'consensus' olmalı"
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

def build_quiz_prompt(quiz_answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build prompt for quiz analysis and supplement recommendations"""
    
    # Extract key information from quiz answers
    profile = []
    if quiz_answers.get("age_range"):
        profile.append(f"Yaş: {quiz_answers['age_range']}")
    if quiz_answers.get("gender"):
        profile.append(f"Cinsiyet: {quiz_answers['gender']}")
    if quiz_answers.get("sleep_pattern"):
        profile.append(f"Uyku düzeni: {quiz_answers['sleep_pattern']}")
    if quiz_answers.get("sleep_hours"):
        profile.append(f"Uyku saati: {quiz_answers['sleep_hours']}")
    if quiz_answers.get("nutrition_type"):
        profile.append(f"Beslenme türü: {quiz_answers['nutrition_type']}")
    if quiz_answers.get("exercise_frequency"):
        profile.append(f"Egzersiz sıklığı: {quiz_answers['exercise_frequency']}")
    if quiz_answers.get("stress_level"):
        profile.append(f"Stres seviyesi: {quiz_answers['stress_level']}")
    if quiz_answers.get("allergies"):
        profile.append(f"Alerjiler: {', '.join(quiz_answers['allergies'])}")
    if quiz_answers.get("health_goals"):
        profile.append(f"Sağlık hedefleri: {', '.join(quiz_answers['health_goals'])}")
    if quiz_answers.get("existing_supplements"):
        profile.append(f"Kullandığı takviyeler: {', '.join(quiz_answers['existing_supplements'])}")
    
    user_profile = "\n".join(profile)
    
    schema = (
        "STRICT JSON ŞEMASI - SUPPLEMENT ÖNERİLERİ:\n"
        "{\n"
        '  "nutrition_advice": {\n'
        '    "title": "Beslenme Önerileri",\n'
        '    "recommendations": ["Öneri 1", "Öneri 2", "Öneri 3"]\n'
        "  },\n"
        '  "lifestyle_advice": {\n'
        '    "title": "Yaşam Tarzı Önerileri",\n'
        '    "recommendations": ["Öneri 1", "Öneri 2", "Öneri 3"]\n'
        "  },\n"
        '  "general_warnings": {\n'
        '    "title": "Genel Uyarılar",\n'
        '    "warnings": ["Uyarı 1", "Uyarı 2", "Uyarı 3"]\n'
        "  },\n"
        '  "supplement_recommendations": [\n'
        "    {\n"
        '      "name": "Vitamin D",\n'
        '      "description": "Kemik sağlığı, bağışıklık sistemi için önemli",\n'
        '      "daily_dose": "600-800 IU (doktorunuza danışın)",\n'
        '      "benefits": ["Kalsiyum emilimini artırır", "Bağışıklık güçlendirir"],\n'
        '      "warnings": ["Yüksek dozlarda toksik olabilir"],\n'
        '      "priority": "high"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "SADECE VE SADECE bu JSON formatında yanıt ver. Hiçbir açıklama, metin ekleme."
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir supplement uzmanısın. "
        "Kullanıcının quiz cevaplarına göre beslenme önerileri, yaşam tarzı önerileri ve "
        "uygun supplement önerileri yap. E-ticaret sitesi için ürün önerileri hazırlıyorsun."
    )
    
    user_prompt = f"Kullanıcı profili:\n{user_profile}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def parallel_quiz_analyze(quiz_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Run quiz analysis with parallel LLMs and synthesis"""
    try:
        messages = build_quiz_prompt(quiz_answers)
        
        # Step 1: Call multiple models in parallel
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.2, 1500): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    # For quiz, we want any valid JSON response
                    if result["content"].strip():
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Quiz model {model} failed: {e}")
                    continue
        
        # Step 2: If no responses, fallback
        if not responses:
            print("All quiz models failed, fallback to single model")
            return quiz_fallback(quiz_answers)
        
        # Step 3: Synthesize with GPT-5 for quiz
        synthesis_prompt = build_quiz_synthesis_prompt(responses)
        final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.1, max_tokens=2000)
        
        final_result["models_used"] = [r["model"] for r in responses]
        final_result["synthesis_model"] = SYNTHESIS_MODEL
        return final_result
        
    except Exception as e:
        print(f"Quiz parallel analyze failed: {e}")
        return quiz_fallback(quiz_answers)

def build_quiz_synthesis_prompt(responses: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Build synthesis prompt for quiz recommendations"""
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir synthesis uzmanısın. "
        "Birden fazla AI modelin verdiği supplement önerilerini inceleyip, "
        "en doğru, tutarlı ve kullanışlı bir FINAL quiz sonucu üret. "
        "\n\nKurallar:"
        "\n1. SADECE JSON formatında yanıt ver"
        "\n2. En uygun supplement önerilerini birleştir"
        "\n3. Çelişkili önerilerde en güvenli olanı seç"
        "\n4. Beslenme ve yaşam tarzı önerilerini de kapsamlı yap"
        "\n5. Dozaj önerilerinde 'doktorunuza danışın' ekle"
        "\n6. Priority: high/medium/low olarak belirle"
    )
    
    responses_text = "\n\n=== MODEL RESPONSES ===\n"
    for i, resp in enumerate(responses, 1):
        responses_text += f"\nMODEL {i} ({resp['model']}):\n{resp['response']}\n"
    
    responses_text += "\n=== SYNTHESIS GÖREV ===\n"
    responses_text += (
        "Yukarıdaki supplement önerilerini analiz et ve en iyi quiz sonucunu oluştur. "
        "E-ticaret sitesi için uygun ürün önerileri hazırla."
    )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": responses_text}
    ]

def quiz_fallback(quiz_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback quiz analysis if parallel fails"""
    messages = build_quiz_prompt(quiz_answers)
    for model in PARALLEL_MODELS:
        try:
            res = call_chat_model(model, messages, temperature=0.2, max_tokens=1500)
            if res["content"].strip():
                res["model_used"] = model
                return res
        except Exception as e:
            print(f"Quiz fallback model {model} failed: {e}")
            continue
    
    # Ultimate fallback
    return {
        "content": '{"error": "Quiz analizi geçici olarak kullanılamıyor"}',
        "model_used": "fallback"
    }

def build_single_lab_prompt(test_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build prompt for single lab test analysis (analysis only, no recommendations)"""
    
    test_info = f"Test Adı: {test_data.get('name', 'Bilinmiyor')}\n"
    test_info += f"Sonuç: {test_data.get('value', 'Yok')} {test_data.get('unit', '')}\n"
    if test_data.get('reference_range'):
        test_info += f"Referans Aralığı: {test_data['reference_range']}\n"
    
    schema = (
        "STRICT JSON ŞEMASI - LAB ANALİZİ (SADECE ANALİZ):\n"
        "{\n"
        '  "analysis": {\n'
        '    "summary": "Test sonucunun kısa yorumu",\n'
        '    "interpretation": "Sonucun anlamı ve önemi",\n'
        '    "reference_comparison": "Referans aralığı ile karşılaştırma",\n'
        '    "clinical_significance": "Klinik önemi",\n'
        '    "follow_up_suggestions": "Takip önerileri (sadece genel tıbbi öneri)"\n'
        "  }\n"
        "}\n\n"
        "SADECE ANALİZ YAP, SUPPLEMENт ÖNERİSİ VERME!"
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar sonuçları analiz uzmanısın. "
        "SADECE ANALİZ yap, supplement ya da ilaç önerisi verme. "
        "Sonuçları yorumla, klinik anlamını açıkla, genel tıbbi takip önerileri ver."
    )
    
    user_prompt = f"Laboratuvar test sonucu:\n{test_info}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def build_multiple_lab_prompt(tests_data: List[Dict[str, Any]], session_count: int) -> List[Dict[str, str]]:
    """Build prompt for multiple lab tests general summary"""
    
    tests_info = f"Toplam Test Seansı: {session_count}\n\n"
    tests_info += "Test Sonuçları:\n"
    for i, test in enumerate(tests_data, 1):
        tests_info += f"{i}. {test.get('name', 'Test')}: {test.get('value', 'Yok')} {test.get('unit', '')}"
        if test.get('reference_range'):
            tests_info += f" (Referans: {test['reference_range']})"
        tests_info += "\n"
    
    schema = (
        "STRICT JSON ŞEMASI - GENEL LAB YORUMU:\n"
        "{\n"
        '  "general_assessment": {\n'
        '    "title": "Genel Sağlık Durumu Değerlendirmesi",\n'
        '    "overall_summary": "Tüm test sonuçlarının genel yorumu",\n'
        '    "patterns_identified": "Tespit edilen paternler ve eğilimler",\n'
        '    "areas_of_concern": "Dikkat edilmesi gereken alanlar",\n'
        '    "positive_aspects": "Olumlu sonuçlar"\n'
        "  },\n"
        '  "overall_status": "normal/dikkat_gerekli/takip_önerilen"\n'
        "}\n\n"
        "SADECE ANALİZ YAP, TEDAVİ ÖNERİSİ VERME!"
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar sonuçları genel değerlendirme uzmanısın. "
        "Birden fazla test sonucunu genel olarak yorumla. "
        "SADECE ANALİZ yap, tedavi ya da ilaç önerisi verme. "
        "Genel sağlık durumu hakkında bilgi ver."
    )
    
    user_prompt = f"Laboratuvar test sonuçları:\n{tests_info}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def parallel_single_lab_analyze(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze single lab test with parallel LLMs"""
    try:
        messages = build_single_lab_prompt(test_data)
        
        # Parallel analysis
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.3, 1200): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result["content"].strip():
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Single lab model {model} failed: {e}")
                    continue
        
        if not responses:
            return single_lab_fallback(test_data)
        
        # Synthesis
        synthesis_prompt = build_lab_synthesis_prompt(responses, "single")
        final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.1, max_tokens=1500)
        
        final_result["models_used"] = [r["model"] for r in responses]
        return final_result
        
    except Exception as e:
        print(f"Single lab analyze failed: {e}")
        return single_lab_fallback(test_data)

def parallel_multiple_lab_analyze(tests_data: List[Dict[str, Any]], session_count: int) -> Dict[str, Any]:
    """Analyze multiple lab tests for general summary"""
    try:
        messages = build_multiple_lab_prompt(tests_data, session_count)
        
        # Parallel analysis
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.3, 1500): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result["content"].strip():
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Multiple lab model {model} failed: {e}")
                    continue
        
        if not responses:
            return multiple_lab_fallback(tests_data, session_count)
        
        # Synthesis
        synthesis_prompt = build_lab_synthesis_prompt(responses, "multiple")
        final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.1, max_tokens=1800)
        
        final_result["models_used"] = [r["model"] for r in responses]
        return final_result
        
    except Exception as e:
        print(f"Multiple lab analyze failed: {e}")
        return multiple_lab_fallback(tests_data, session_count)

def build_lab_synthesis_prompt(responses: List[Dict[str, str]], analysis_type: str) -> List[Dict[str, str]]:
    """Build synthesis prompt for lab analysis"""
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar analizi synthesis uzmanısın. "
        "Birden fazla AI modelin verdiği lab analizlerini inceleyip, "
        "en doğru ve kapsamlı analizi üret. "
        "\n\nKurallar:"
        "\n1. SADECE JSON formatında yanıt ver"
        "\n2. SADECE ANALİZ yap, supplement/ilaç önerisi verme"
        "\n3. En doğru ve tutarlı yorumu birleştir"
        "\n4. Klinik anlamı net açıkla"
        "\n5. Genel tıbbi takip önerileri ver"
    )
    
    responses_text = "\n\n=== MODEL RESPONSES ===\n"
    for i, resp in enumerate(responses, 1):
        responses_text += f"\nMODEL {i} ({resp['model']}):\n{resp['response']}\n"
    
    task_desc = "tek test analizi" if analysis_type == "single" else "genel test özeti"
    responses_text += f"\n=== SYNTHESIS GÖREV ===\n"
    responses_text += f"Yukarıdaki {task_desc} sonuçlarını analiz et ve en iyi laboratuvar yorumu oluştur."
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": responses_text}
    ]

def single_lab_fallback(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback for single lab analysis"""
    return {
        "content": '{"analysis": {"summary": "Test analizi geçici olarak kullanılamıyor", "interpretation": "Lütfen daha sonra tekrar deneyin"}}',
        "model_used": "fallback"
    }

def multiple_lab_fallback(tests_data: List[Dict[str, Any]], session_count: int) -> Dict[str, Any]:
    """Fallback for multiple lab analysis"""
    return {
        "content": f'{{"general_assessment": {{"title": "Genel Sağlık Durumu", "overall_summary": "Analiz sistemi geçici olarak kullanılamıyor"}}, "overall_status": "geçici_bakım"}}',
        "model_used": "fallback"
    }

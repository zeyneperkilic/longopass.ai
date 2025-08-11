from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import json, time

from .config import ALLOWED_ORIGINS, CHAT_HISTORY_MAX, FREE_ANALYZE_LIMIT, DAILY_CHAT_LIMIT
from .db import Base, engine, SessionLocal, User, Conversation, Message, MessageMeta
from .auth import get_db, get_or_create_user
from .schemas import AnalyzePayload, LabBatchPayload, ChatStartResponse, ChatMessageRequest, ChatResponse, AnalyzeResponse, QuizRequest, QuizResponse, SingleLabRequest, MultipleLabRequest, LabAnalysisResponse, GeneralLabSummaryResponse
from .health_guard import guard_or_message
from .orchestrator import cascade_chat, finalize_text, cascade_analyze, finalize_analyze, parallel_quiz_analyze, parallel_single_lab_analyze, parallel_multiple_lab_analyze
from .utils import parse_json_safe

app = FastAPI(title="Longopass AI Gateway")
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS!=["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve widget js and static frontend (optional)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "longopass-ai"}

@app.get("/widget.js")
def widget_js():
    with open("frontend/widget.js", "r", encoding="utf-8") as f:
        return f.read()

# ---------- CHAT (PREMIUM) ----------

@app.post("/ai/chat/start", response_model=ChatStartResponse)
def chat_start(db: Session = Depends(get_db),
               x_user_id: str | None = Header(default=None),
               x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    if user.plan != "premium":
        raise HTTPException(403, "Chat için premium gereklidir.")
    conv = Conversation(user_id=user.id, status="active")
    db.add(conv); db.commit(); db.refresh(conv)
    return ChatStartResponse(conversation_id=conv.id)

@app.get("/ai/chat/{conversation_id}/history")
def chat_history(conversation_id: int,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    conv = db.query(Conversation).filter(Conversation.id==conversation_id, Conversation.user_id==user.id).first()
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")
    msgs = db.query(Message).filter(Message.conversation_id==conv.id).order_by(Message.created_at.asc()).all()
    return [{"role": m.role, "content": m.content, "ts": m.created_at.isoformat()} for m in msgs][-CHAT_HISTORY_MAX:]

@app.post("/ai/chat", response_model=ChatResponse)
def chat_message(req: ChatMessageRequest,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    if user.plan != "premium":
        raise HTTPException(403, "Chat için premium gereklidir.")

    conv = db.query(Conversation).filter(Conversation.id==req.conversation_id, Conversation.user_id==user.id).first()
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    # Simple daily chat limit per user
    if DAILY_CHAT_LIMIT > 0:
        import datetime
        start_of_day = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        todays_msgs = db.query(Message).filter(
            Message.user_id==user.id,
            Message.created_at >= start_of_day,
            Message.role == "user"
        ).count()
        if todays_msgs >= DAILY_CHAT_LIMIT:
            raise HTTPException(429, "Günlük sohbet limitine ulaştınız. Lütfen yarın tekrar deneyin.")

    ok, msg = guard_or_message(req.text)
    if not ok:
        # store user message
        db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=req.text)); db.commit()
        # reply fixed message
        reply = msg
        m = Message(conversation_id=conv.id, role="assistant", content=reply, model_name="guard", model_latency_ms=0)
        db.add(m); db.commit()
        return ChatResponse(conversation_id=conv.id, reply=reply, used_model="guard", latency_ms=0)

    # build history
    rows = db.query(Message).filter(Message.conversation_id==conv.id).order_by(Message.created_at.asc()).all()
    history = [{"role": "system", "content": "Sen Longopass AI'sın. SADECE sağlık/supplement/lab konularında yanıt ver. Off-topic'te kibarca reddet."}]
    for r in rows[-(CHAT_HISTORY_MAX-1):]:
        history.append({"role": r.role, "content": r.content})
    history.append({"role": "user", "content": req.text})

    # store user message
    db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=req.text)); db.commit()

    # cascade
    start = time.time()
    res = cascade_chat(history)
    candidate = res["content"]
    used_model = res.get("model_used","unknown")
    # finalize
    final = finalize_text(candidate)
    latency_ms = int((time.time()-start)*1000)

    # store assistant message + meta
    m = Message(conversation_id=conv.id, role="assistant", content=final, model_name=used_model, model_latency_ms=latency_ms)
    db.add(m); db.commit(); db.refresh(m)
    db.add(MessageMeta(message_id=m.id, raw_provider_payload=res.get("raw"), raw_provider_name=used_model))
    db.commit()

    return ChatResponse(conversation_id=conv.id, reply=final, used_model=used_model, latency_ms=latency_ms)

# ---------- ANALYZE (FREE: one-time), LAB ----------

def count_user_analyses(db: Session, user_id: int) -> int:
    # Count 'analyze' requests stored as system messages tagged? Simpler: count assistant messages with model_name like 'analyze'
    return db.query(Message).filter(Message.user_id==user_id, Message.role=="assistant", Message.model_name=="analyze").count()

@app.post("/ai/quiz", response_model=QuizResponse)
def analyze_quiz(body: QuizRequest,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    if user.plan == "free" and count_user_analyses(db, user.id) >= FREE_ANALYZE_LIMIT:
        raise HTTPException(403, "Ücretsiz kullanıcılar yalnızca bir kez analiz yapabilir. Premium'a yükseltin.")

    # Convert quiz answers to dict for health guard
    quiz_dict = body.answers.model_dump()
    ok, msg = guard_or_message(json.dumps(quiz_dict))
    if not ok:
        raise HTTPException(400, msg)

    # Use parallel quiz analysis
    res = parallel_quiz_analyze(quiz_dict)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Store quiz result
    db.add(Message(user_id=user.id, conversation_id=None, role="assistant", content=final_json, model_name="quiz"))
    db.commit()
    return data

@app.post("/ai/lab/single", response_model=LabAnalysisResponse)
def analyze_single_lab(body: SingleLabRequest,
                       db: Session = Depends(get_db),
                       x_user_id: str | None = Header(default=None),
                       x_user_plan: str | None = Header(default=None)):
    """Analyze single lab test result (analysis only, no recommendations)"""
    user = get_or_create_user(db, x_user_id, x_user_plan)
    
    # Convert test to dict for health guard
    test_dict = body.test.model_dump()
    ok, msg = guard_or_message(json.dumps(test_dict))
    if not ok:
        raise HTTPException(400, msg)

    # Use parallel single lab analysis
    res = parallel_single_lab_analyze(test_dict)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Store single lab analysis
    db.add(Message(user_id=user.id, conversation_id=None, role="assistant", content=final_json, model_name="single_lab"))
    db.commit()
    return data

@app.post("/ai/lab/summary", response_model=GeneralLabSummaryResponse)
def analyze_multiple_lab_summary(body: MultipleLabRequest,
                                 db: Session = Depends(get_db),
                                 x_user_id: str | None = Header(default=None),
                                 x_user_plan: str | None = Header(default=None)):
    """Generate general summary of multiple lab tests"""
    user = get_or_create_user(db, x_user_id, x_user_plan)
    
    # Convert tests to dict for health guard
    tests_dict = [test.model_dump() for test in body.tests]
    ok, msg = guard_or_message(json.dumps(tests_dict))
    if not ok:
        raise HTTPException(400, msg)

    # Use parallel multiple lab analysis
    res = parallel_multiple_lab_analyze(tests_dict, body.total_test_sessions)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Add metadata for response formatting
    if "test_count" not in data:
        data["test_count"] = body.total_test_sessions
    if "overall_status" not in data:
        data["overall_status"] = "analiz_tamamlandı"
    
    # Store multiple lab summary
    db.add(Message(user_id=user.id, conversation_id=None, role="assistant", content=final_json, model_name="multiple_lab"))
    db.commit()
    return data

# Legacy lab endpoint for backward compatibility
@app.post("/ai/lab/analyze", response_model=AnalyzeResponse)
def analyze_lab_legacy(body: LabBatchPayload,
                       db: Session = Depends(get_db),
                       x_user_id: str | None = Header(default=None),
                       x_user_plan: str | None = Header(default=None)):
    """Legacy lab analysis endpoint (supplement recommendations)"""
    user = get_or_create_user(db, x_user_id, x_user_plan)
    ok, msg = guard_or_message(json.dumps(body.results))
    if not ok:
        raise HTTPException(400, msg)

    res = cascade_analyze({"lab_results": body.results})
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    db.add(Message(user_id=user.id, conversation_id=None, role="assistant", content=final_json, model_name="lab_legacy"))
    db.commit()
    return data

@app.get("/debug/analyze")
def debug_analyze():
    """Debug endpoint to see raw LLM response"""
    from .orchestrator import build_analyze_prompt
    from .openrouter_client import call_chat_model
    from .config import CASCADE_MODELS
    import traceback
    
    test_payload = {"belirtiler": "Yorgunluk, saç dökülmesi, konsantrasyon problemi"}
    messages = build_analyze_prompt(test_payload)
    
    # Test first model in cascade
    model = CASCADE_MODELS[0] 
    
    try:
        res = call_chat_model(model, messages, temperature=0.3, max_tokens=2000)
        
        from .utils import is_valid_analyze
        is_valid, error = is_valid_analyze(res["content"])
        
        return {
            "model": model,
            "messages_sent": messages,
            "full_openrouter_response": res,
            "raw_response": res["content"], 
            "is_valid": is_valid,
            "validation_error": error,
            "parsed": parse_json_safe(res["content"]),
            "success": True
        }
    except Exception as e:
        return {
            "model": model,
            "messages_sent": messages,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "success": False
        }

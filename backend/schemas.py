from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Any

class AnalyzePayload(BaseModel):
    payload: Dict[str, Any]

class LabBatchPayload(BaseModel):
    results: List[Dict[str, Any]]

class ChatStartResponse(BaseModel):
    conversation_id: int

class ChatMessageRequest(BaseModel):
    conversation_id: int
    text: str

class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    used_model: str
    latency_ms: int

class RecommendationItem(BaseModel):
    id: Optional[str] = None
    name: str
    reason: str
    source: Literal["consensus", "assistant"] = "consensus"

class AnalyzeResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."


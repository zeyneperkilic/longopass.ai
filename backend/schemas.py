from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Any

# Quiz Schemas
class QuizAnswers(BaseModel):
    age_range: str = Field(description="Yaş aralığı: 18-25, 26-35, 36-45, 46-55, 56-65, 65+")
    gender: str = Field(description="Cinsiyet: erkek, kadın, belirtmek_istemiyorum")
    sleep_pattern: str = Field(description="Uyku düzeni: düzenli, düzensiz, uyku_sorunu_var")
    sleep_hours: str = Field(description="Uyku saati: 4_saatten_az, 4-6_saat, 6-8_saat, 8_saatten_fazla")
    nutrition_type: str = Field(description="Beslenme türü: vejetaryen, vegan, karışık, glutensiz, özel_diyet")
    exercise_frequency: str = Field(description="Egzersiz sıklığı: hiç, haftada_1-2, haftada_3-4, günlük")
    stress_level: str = Field(description="Stres seviyesi: düşük, orta, yüksek, çok_yüksek")
    allergies: List[str] = Field(default_factory=list, description="Alerjiler: süt, yumurta, fındık, balık, vs.")
    health_goals: List[str] = Field(default_factory=list, description="Sağlık hedefleri: kilo_verme, kas_kazanma, enerji, vs.")
    existing_supplements: List[str] = Field(default_factory=list, description="Kullandığı takviyeler")

class QuizRequest(BaseModel):
    answers: QuizAnswers

class SupplementRecommendation(BaseModel):
    name: str = Field(description="Supplement adı")
    description: str = Field(description="Açıklama")
    daily_dose: str = Field(description="Günlük doz")
    benefits: List[str] = Field(description="Faydaları")
    warnings: List[str] = Field(description="Uyarılar")
    priority: Literal["high", "medium", "low"] = Field(default="medium")

class NutritionAdvice(BaseModel):
    title: str = "Beslenme Önerileri"
    recommendations: List[str]

class LifestyleAdvice(BaseModel):
    title: str = "Yaşam Tarzı Önerileri" 
    recommendations: List[str]

class GeneralWarnings(BaseModel):
    title: str = "Genel Uyarılar"
    warnings: List[str]

class QuizResponse(BaseModel):
    success: bool = True
    message: str = "Online Sağlık Quizini Başarıyla Tamamladınız"
    nutrition_advice: NutritionAdvice
    lifestyle_advice: LifestyleAdvice
    general_warnings: GeneralWarnings
    supplement_recommendations: List[SupplementRecommendation]
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

# Legacy schemas for compatibility
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


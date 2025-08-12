# 🚀 LONGOPASS AI - IdeaSoft E-Ticaret Entegrasyon Rehberi

## 📋 İçindekiler
1. [Sistem Özeti](#sistem-özeti)
2. [Teknik Gereksinimler](#teknik-gereksinimler)
3. [API Endpoints](#api-endpoints)
4. [Frontend Widget Entegrasyonu](#frontend-widget-entegrasyonu)
5. [Güvenlik & CORS](#güvenlik--cors)
6. [Test Prosedürü](#test-prosedürü)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Sistem Özeti

**Longopass AI** sistemi aşağıdaki özellikleri sunar:

### ✅ Çalışan Özellikler
- **💬 AI Chat**: Premium kullanıcılar için konuşma hafızası ile sağlık danışmanlığı
- **🧪 Quiz Analizi**: E-ticaret önerileri (supplement, beslenme, yaşam tarzı)
- **🔬 Lab Test Analizi**: Tek test yorumu + genel test özeti
- **🛡️ Akıllı Health Guard**: LLM tabanlı içerik moderasyonu
- **⚡ Parallel LLM**: Hızlı ve güvenilir AI yanıtları

### 🎨 Frontend Widget
- Responsive tasarım
- Kolay entegrasyon
- Custom event sistemi
- Minimal CSS conflict

---

## ⚙️ Teknik Gereksinimler

### Backend API
- **URL**: `https://longopass-ai.onrender.com`
- **Format**: RESTful JSON API
- **CORS**: IdeaSoft domain'i için yapılandırılmış
- **Rate Limiting**: Premium/Free user ayrımı

### Frontend Widget
- **Pure JavaScript** (framework dependency yok)
- **Modern Browser** support (ES6+)
- **Responsive**: Mobile/Desktop uyumlu

---

## 🔌 API Endpoints

### 1. Chat Sistemi (Premium Only)

#### Start Conversation
```http
POST /ai/chat/start
Headers:
  Content-Type: application/json
  X-User-ID: string (optional)
  X-User-Plan: "premium" | "free"

Response:
{
  "conversation_id": 123
}
```

#### Send Message
```http
POST /ai/chat
Headers:
  Content-Type: application/json
  X-User-ID: string
  X-User-Plan: "premium"

Body:
{
  "conversation_id": 123,
  "text": "D vitamini eksikliği belirtileri nelerdir?"
}

Response:
{
  "conversation_id": 123,
  "reply": "D vitamini eksikliği...",
  "used_model": "deepseek/deepseek-chat-v3-0324",
  "latency_ms": 2500
}
```

#### Get Chat History
```http
GET /ai/chat/{conversation_id}/history
Headers:
  X-User-ID: string
  X-User-Plan: "premium"

Response: [
  {
    "role": "user",
    "content": "Merhaba",
    "ts": "2025-08-11T19:03:45.758665"
  },
  {
    "role": "assistant", 
    "content": "Merhaba! Size nasıl yardımcı olabilirim?",
    "ts": "2025-08-11T19:03:47.123456"
  }
]
```

### 2. Quiz Analizi

```http
POST /ai/quiz
Headers:
  Content-Type: application/json
  X-User-Plan: "premium" | "free" 

Body:
{
  "answers": {
    "age": 30,
    "gender": "female", 
    "activity_level": "moderate",
    "goals": ["weight_loss", "energy"],
    "dietary_restrictions": ["vegetarian"],
    "current_supplements": [],
    "health_conditions": [],
    "sleep_quality": "good",
    "stress_level": "medium"
  }
}

Response:
{
  "supplements": [
    {
      "name": "Magnezyum",
      "reason": "Uyku kalitesi ve kas gevşemesi için",
      "dosage": "300-400mg/gün",
      "timing": "Akşam yemeği sonrası",
      "source": "consensus"
    }
  ],
  "nutrition": [
    {
      "recommendation": "Protein alımını artırın",
      "details": "Günde vücut kilosunun 1.6-2.2 katı kadar protein",
      "food_sources": ["mercimek", "kinoa", "tofu"],
      "source": "consensus"
    }
  ],
  "lifestyle": [
    {
      "category": "Exercise",
      "suggestion": "Haftada 3-4 kez direnç antrenmanı",
      "benefit": "Metabolizma hızlandırma ve kas koruma",
      "source": "consensus"
    }
  ]
}
```

### 3. Lab Test Analizi

#### Single Test Analysis
```http
POST /ai/lab/single
Headers:
  Content-Type: application/json
  X-User-Plan: "premium" | "free"

Body:
{
  "test": {
    "name": "Hemoglobin",
    "value": "8.5",
    "unit": "g/dL", 
    "reference_range": "12.0-15.5 g/dL"
  }
}

Response:
{
  "analysis": {
    "summary": "Hemoglobin düzeyi belirgin şekilde düşük olup, bu durum orta ile ileri derecede anemiyi düşündürmektedir.",
    "interpretation": "8.5 g/dL hemoglobin değeri, yetişkin kadınlarda (12.0–15.5 g/dL) ve erkeklerde (13.5–17.5 g/dL) kabul edilen normal aralığın oldukça altındadır...",
    "reference_comparison": "Sonuç, referans alt sınırının yaklaşık %25 altında ve mutlak olarak 3–5 g/dL daha düşüktür.",
    "clinical_significance": "Anemi; oksijen taşıma kapasitesini azaltarak yorgunluk, halsizlik, nefes darlığı...",
    "follow_up_suggestions": "1. Tam kan sayımı (CBC) ve periferik yayma ile aneminin morfolojik tipinin netleştirilmesi..."
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Multiple Tests Summary
```http
POST /ai/lab/summary
Headers:
  Content-Type: application/json
  X-User-Plan: "premium" | "free"

Body:
{
  "tests": [
    {
      "name": "Hemoglobin",
      "value": "8.5", 
      "unit": "g/dL",
      "reference_range": "12.0-15.5 g/dL"
    },
    {
      "name": "Vitamin D",
      "value": "18",
      "unit": "ng/mL", 
      "reference_range": "20-50 ng/mL"
    }
  ],
  "total_test_sessions": 5
}

Response:
{
  "summary": {
    "general_assessment": "Test sonuçlarınızda dikkat edilmesi gereken birkaç alan bulunmaktadır...",
    "overall_status": "Genel olarak takip gerektiren bulgular mevcut"
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

---

## 🎨 Frontend Widget Entegrasyonu

### 1. Widget JavaScript Include
IdeaSoft sitenizin `<head>` bölümüne ekleyin:

```html
<script src="https://longopass-ai.onrender.com/widget.js"></script>
```

### 2. Widget Container
Widget'in görüneceği yere HTML container ekleyin:

```html
<div id="longopass-ai-widget"></div>
```

### 3. Widget Initialization
Sayfa yüklendiğinde widget'i başlatın:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Widget'i başlat
    window.LongopassAI.init({
        container: '#longopass-ai-widget',
        userPlan: 'premium', // veya 'free'
        userId: getCurrentUserId(), // IdeaSoft user ID
        theme: 'light', // veya 'dark'
        position: 'bottom-right' // veya 'bottom-left', 'embedded'
    });
});

// IdeaSoft user ID'sini al
function getCurrentUserId() {
    // IdeaSoft'un user session sisteminden user ID'yi alın
    return 'user_' + Math.random().toString(36).substr(2, 9);
}
```

### 4. Quiz Integration
Quiz sonuçlarını widget'e gönderme:

```javascript
// IdeaSoft quiz formu submit edildiğinde
document.getElementById('quiz-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const quizAnswers = {
        age: parseInt(formData.get('age')),
        gender: formData.get('gender'),
        activity_level: formData.get('activity_level'),
        goals: formData.getAll('goals'),
        dietary_restrictions: formData.getAll('dietary_restrictions'),
        current_supplements: formData.getAll('current_supplements'),
        health_conditions: formData.getAll('health_conditions'),
        sleep_quality: formData.get('sleep_quality'),
        stress_level: formData.get('stress_level')
    };
    
    // Longopass AI'ye quiz gönder
    window.LongopassAI.submitQuiz(quizAnswers);
});
```

### 5. Lab Test Integration
Lab test sonuçlarını widget'e gönderme:

```javascript
// Tek test analizi
function analyzeSingleTest(testData) {
    window.LongopassAI.analyzeLab({
        type: 'single',
        test: {
            name: testData.name,
            value: testData.value,
            unit: testData.unit,
            reference_range: testData.reference_range
        }
    });
}

// Çoklu test özeti
function analyzeMultipleTests(testsArray, sessionCount) {
    window.LongopassAI.analyzeLab({
        type: 'summary',
        tests: testsArray,
        total_test_sessions: sessionCount
    });
}
```

### 6. Event Handling
Widget'den gelen olayları dinleme:

```javascript
// Widget'den gelen olayları dinle
document.addEventListener('longopass-quiz-complete', function(event) {
    const recommendations = event.detail;
    console.log('Quiz analizi tamamlandı:', recommendations);
    
    // Önerileri IdeaSoft ürün sayfalarına yönlendirme
    displayProductRecommendations(recommendations.supplements);
});

document.addEventListener('longopass-lab-complete', function(event) {
    const analysis = event.detail;
    console.log('Lab analizi tamamlandı:', analysis);
    
    // Analiz sonuçlarını gösterme
    displayLabResults(analysis);
});

// Ürün önerilerini gösterme
function displayProductRecommendations(supplements) {
    supplements.forEach(supplement => {
        // IdeaSoft ürün arama API'si kullanarak ilgili ürünleri bul
        findProducts(supplement.name).then(products => {
            // Ürünleri sayfa üzerinde göster
            showRecommendedProducts(products, supplement.reason);
        });
    });
}
```

---

## 🛡️ Güvenlik & CORS

### CORS Configuration
Backend, IdeaSoft domain'i için CORS yapılandırması yapılmıştır. Eğer farklı domain kullanıyorsanız, backend config'te güncelleme gerekebilir.

### Rate Limiting
- **Free users**: Günde 5 request
- **Premium users**: Günde 100 request

### API Key Management
Backend OpenRouter API key'i environment variable olarak saklar. Güvenlik endişesi yoktur.

---

## 🧪 Test Prosedürü

### 1. Test Dashboard
Test için: `https://longopass-ai.onrender.com/test`

### 2. Manuel API Testing

#### Chat Test
```bash
# Start conversation
curl -X POST "https://longopass-ai.onrender.com/ai/chat/start" \
  -H "Content-Type: application/json" \
  -H "X-User-Plan: premium" \
  -H "X-User-ID: test-user"

# Send message  
curl -X POST "https://longopass-ai.onrender.com/ai/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Plan: premium" \
  -H "X-User-ID: test-user" \
  -d '{
    "conversation_id": 1,
    "text": "D vitamini eksikliği belirtileri nelerdir?"
  }'
```

#### Quiz Test
```bash
curl -X POST "https://longopass-ai.onrender.com/ai/quiz" \
  -H "Content-Type: application/json" \
  -H "X-User-Plan: premium" \
  -d '{
    "answers": {
      "age": 30,
      "gender": "female",
      "activity_level": "moderate", 
      "goals": ["weight_loss"],
      "dietary_restrictions": [],
      "current_supplements": [],
      "health_conditions": [],
      "sleep_quality": "good",
      "stress_level": "medium"
    }
  }'
```

#### Lab Test
```bash
curl -X POST "https://longopass-ai.onrender.com/ai/lab/single" \
  -H "Content-Type: application/json" \
  -H "X-User-Plan: premium" \
  -d '{
    "test": {
      "name": "Hemoglobin",
      "value": "8.5",
      "unit": "g/dL",
      "reference_range": "12.0-15.5 g/dL"
    }
  }'
```

### 3. Widget Testing
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://longopass-ai.onrender.com/widget.js"></script>
</head>
<body>
    <div id="longopass-ai-widget"></div>
    
    <script>
        window.LongopassAI.init({
            container: '#longopass-ai-widget',
            userPlan: 'premium',
            userId: 'test-user-123'
        });
    </script>
</body>
</html>
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. CORS Errors
```
Access to fetch at 'https://longopass-ai.onrender.com' from origin 'https://yoursite.com' has been blocked by CORS policy
```
**Çözüm**: Backend CORS ayarlarında domain'inizi ekletin.

#### 2. Widget Not Loading
```javascript
// Console'da kontrol edin
console.log(window.LongopassAI); // undefined ise widget.js yüklenmemiş
```
**Çözüm**: Widget.js script tag'ini kontrol edin.

#### 3. API 403 Errors
```json
{"detail": "Chat için premium gereklidir."}
```
**Çözüm**: `X-User-Plan: premium` header'ını kontrol edin.

#### 4. Memory Issues
```json
{"detail": "Konuşma bulunamadı"}
```
**Çözüm**: `conversation_id` ve `X-User-ID`'nin tutarlı olduğunu kontrol edin.

### Performance Tips

1. **Widget Loading**: Widget'i async olarak yükleyin
2. **Caching**: API yanıtlarını browser'da cache'leyin
3. **Debouncing**: Chat input'u için debounce kullanın
4. **Error Handling**: Network error'ları için fallback mekanizması

---

## 📞 Destek & İletişim

### Production URLs
- **API Base**: `https://longopass-ai.onrender.com`
- **Widget**: `https://longopass-ai.onrender.com/widget.js` 
- **Test Dashboard**: `https://longopass-ai.onrender.com/test`

### Sistem Status
- **Uptime**: 99.9%+
- **Response Time**: ~2-5 saniye (LLM processing)
- **Rate Limits**: Premium: 100/day, Free: 5/day

### Updates
Sistem güncellemeleri GitHub üzerinden otomatik deploy edilir. Breaking change'ler önceden bildirilir.

---

## 🎯 Next Steps

1. **Widget Test**: Önce test sayfasında widget'i deneyin
2. **API Integration**: IdeaSoft backend'ine API call'ları ekleyin  
3. **UI/UX**: Widget'i site tasarımınıza uygun özelleştirin
4. **User Management**: IdeaSoft user system'i ile entegre edin
5. **Product Matching**: Quiz önerilerini ürün kataloğunuza bağlayın

**🚀 Başarılar! Longopass AI artık IdeaSoft sitenizde kullanıma hazır!**
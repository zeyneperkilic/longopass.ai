# 🚀 Longopass AI - Hızlı Entegrasyon Rehberi

**IdeaSoft Developer'ı için basit adımlar - sadece AI entegrasyonu**

---

## 📋 1. Widget JavaScript Ekleme

### HTML head'e ekle:
```html
<script src="https://longopass-ai.onrender.com/widget.js"></script>
```

---

## 📋 2. Quiz Entegrasyonu 

### Mevcut quiz formunuzun submit handler'ına ekle:

```javascript
// Quiz form submit olduğunda
document.getElementById('your-quiz-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Form verilerini topla
    const formData = new FormData(e.target);
    const quizAnswers = {
        age: parseInt(formData.get('age')),
        gender: formData.get('gender'),
        activity_level: formData.get('activity_level'),
        goals: formData.getAll('goals'),
        dietary_restrictions: formData.getAll('dietary_restrictions'),
        current_supplements: [],
        health_conditions: [],
        sleep_quality: formData.get('sleep_quality'),
        stress_level: formData.get('stress_level')
    };
    
    // Longopass AI'ye gönder
    fetch('https://longopass-ai.onrender.com/ai/quiz', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-User-Plan': 'premium', // veya 'free'
            'X-User-ID': getCurrentUserId() // sizin user ID fonksiyonunuz
        },
        body: JSON.stringify({ answers: quizAnswers })
    })
    .then(response => response.json())
    .then(data => {
        // AI önerilerini göster
        displayRecommendations(data);
    });
});
```

---

## 📋 3. Lab Test Entegrasyonu

### Tek test analizi için:
```javascript
function analyzeSingleTest(testName, testValue, testUnit, referenceRange) {
    fetch('https://longopass-ai.onrender.com/ai/lab/single', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-User-Plan': 'premium',
            'X-User-ID': getCurrentUserId()
        },
        body: JSON.stringify({
            test: {
                name: testName,
                value: testValue,
                unit: testUnit,
                reference_range: referenceRange
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        // Test analizini göster
        displayLabResults(data);
    });
}
```

### Çoklu test özeti için:
```javascript
function analyzeMultipleTests(testsArray, sessionCount) {
    fetch('https://longopass-ai.onrender.com/ai/lab/summary', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-User-Plan': 'premium',
            'X-User-ID': getCurrentUserId()
        },
        body: JSON.stringify({
            tests: testsArray,
            total_test_sessions: sessionCount
        })
    })
    .then(response => response.json())
    .then(data => {
        // Genel özeti göster
        displayLabSummary(data);
    });
}
```

---

## 📋 4. Chat Widget Ekleme

### Body'nin sonuna ekle:
```html
<div id="longopass-chat-widget"></div>

<script>
// Sayfa yüklendiğinde chat widget'i başlat
document.addEventListener('DOMContentLoaded', function() {
    if (window.LongopassAI) {
        window.LongopassAI.init({
            container: '#longopass-chat-widget',
            userPlan: getUserPlan(), // 'premium' veya 'free'
            userId: getCurrentUserId(),
            position: 'bottom-right'
        });
    }
});
</script>
```

---

## 📋 5. Ürün Önerilerini Gösterme

### Quiz sonuçlarından ürün önerileri:
```javascript
function displayRecommendations(aiResults) {
    if (aiResults.supplements) {
        aiResults.supplements.forEach(supplement => {
            // Sitenizde bu supplement'i arayın
            const matchingProducts = findProductsByName(supplement.name);
            
            // Ürünleri öneriler bölümünde gösterin
            showProductRecommendation(matchingProducts, supplement.reason);
        });
    }
}

// Örnek ürün arama fonksiyonu (sizin sisteminize uyarlayın)
function findProductsByName(supplementName) {
    // IdeaSoft ürün arama API'nizi kullanın
    // Örnek: /api/products/search?q=supplementName
    return []; // Bulunan ürünler
}
```

---

## 📋 6. User ID ve Plan Fonksiyonları

### Gerekli helper fonksiyonları:
```javascript
// Mevcut kullanıcının ID'sini al
function getCurrentUserId() {
    // IdeaSoft'un user session sisteminden user ID'yi döndürün
    return 'user_' + (window.currentUser?.id || 'anonymous');
}

// Kullanıcının planını al  
function getUserPlan() {
    // Premium/free kontrolü
    return window.currentUser?.isPremium ? 'premium' : 'free';
}
```

---

## 📋 7. CORS Ayarı (Opsiyonel)

Eğer CORS hatası alırsanız, domain'inizi backend'e ekletmek için iletişime geçin:
- **Your domain**: `https://yoursite.com`

---

## 🎯 Özet - Sadece Bu 3 Dosyayı Düzenleyin:

1. **Layout/Master dosyasına**: Widget script'i ekle
2. **Quiz sayfasına**: Quiz submit handler'ı ekle  
3. **Lab test sayfasına**: Test analiz fonksiyonları ekle

**Hepsi bu kadar!** 🎉

---

## 📞 Test

Test için: `https://longopass-ai.onrender.com/test`

Herhangi bir sorun olursa bizimle iletişime geçin.
# Longopass AI Gateway – Deploy Quickstart

## Environment (.env)

```
OPENROUTER_API_KEY=YOUR_KEY
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
CASCADE_MODELS=google/gemini-2.5-pro,x-ai/grok-2,deepseek/deepseek-r1,meta-llama/llama-3.1-8b-instruct
FINALIZER_MODEL=openai/gpt-5
HEALTH_MODE=topic
MODERATION_MODEL=meta-llama/llama-3.1-8b-instruct
DAILY_CHAT_LIMIT=100
FREE_ANALYZE_LIMIT=1
ALLOWED_ORIGINS=https://www.siteniz.com
CASCADE_TIMEOUT_MS=8000
CHAT_HISTORY_MAX=20
DB_PATH=/app/app.db
```

## Docker

```
docker build -t longopass-ai .
mkdir -p /srv/longopass-ai/data
docker run -d --name longopass-ai \
  -p 8000:8000 \
  --env-file .env \
  -v /srv/longopass-ai/data:/app \
  longopass-ai
```

## Nginx (example)

```
server {
  server_name ai.siteniz.com;
  listen 443 ssl http2;
  # ssl_certificate ...; ssl_certificate_key ...;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_read_timeout 120s;
  }
}
```

## IdeaSoft embed

```
<script>
  window.LONGOPASS_AI_BASE = 'https://ai.siteniz.com';
  window.LONGOPASS_USER_ID = '';
  window.LONGOPASS_PLAN = 'premium';
</script>
<script src="https://ai.siteniz.com/widget.js" defer></script>
```

# Longopass AI Gateway (Cascade + Finalizer)

Bu paket, OpenRouter tek API ile **Cascade (Llama → DeepSeek → Gemini → Grok)** ve en sonda **GPT-5 finalizer** akışını sunan mini bir AI servisidir. IdeaSoft sitenize **tek satır script** ile gömülebilir.

## Özellikler
- **/ai/quiz**: Free kullanıcı 1 kez; premium sınırsız. Öneri JSON'u döner.
- **/ai/lab/analyze**: Tekil veya toplu laboratuvar analizi.
- **/ai/chat**: Premium chatbot; sağlık dışı soruları reddeder; geçmişi hatırlar.
- **Cascade**: Ucuzdan pahalıya (Llama → DeepSeek → Gemini → Grok) ilk geçerli yanıtı seçer.
- **Finalizer**: GPT-5 ile format/tekilleştirme/ton düzeltme, yeni bilgi eklemeden.
- **Widget**: `widget.js` ile chat balonu ve “AI ile analiz et” butonları.

## Kurulum
1. Depoyu sunucunuza çıkarın.
2. `.env` oluşturun (bkz: `.env.example`) ve `OPENROUTER_API_KEY` girin.
3. Bağımlılıklar:
   ```bash
   pip install -r requirements.txt
   ```
4. Sunucu:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
5. Tarayıcıda açın: `http://localhost:8000` → demo için `frontend/index.html` statik dosya sunulur.
6. IdeaSoft'a ekleyin:
   ```html
   <script src="https://ai.longopass.com/widget.js" defer></script>
   ```
   > `ai.longopass.com` yerine kendi gateway host'unuzu yazın. CORS için `.env`'de `ALLOWED_ORIGINS`'e sitenizi ekleyin.

## Entegrasyon
- **Quiz** sayfasına `id="lp-ai-quiz-btn"` olan bir buton ekleyin.
- **Lab** sayfasına `id="lp-ai-lab-btn"` olan bir buton ekleyin.
- `widget.js` bu butonları otomatik tanır ve AI servislerine çağrı yapar.

## Başlıklar (Auth Basitleştirmesi)
- `X-User-Id`: Kullanıcı kimliği (zorunlu değil; yoksa guest).
- `X-User-Plan`: `free` veya `premium` (demo için). Gerçekte sizin sunucunuzdan alınmalı.

## Notlar
- Model slug'larını OpenRouter panelinizden kontrol edin ve `.env`'de `CASCADE_MODELS` / `FINALIZER_MODEL` değerlerini güncelleyin.
- OpenRouter çağrıları OpenAI-uyumlu `/chat/completions` ile yapılır.
- Gizlilik: Sağlık dışı sorular guard tarafından reddedilir. Çıktılara otomatik “bilgilendirme amaçlıdır” uyarısı eklenir.

## Örnek .env
```
# === OpenRouter ===
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
OPENROUTER_BASE_URL=https://api.openrouter.ai/v1

# === Cascade & Finalizer ===
# Order: cheapest/fastest -> strongest
CASCADE_MODELS=meta-llama/llama-3.1-8b-instruct,deepseek/deepseek-r1,google/gemini-2.5-pro,x-ai/grok-2
FINALIZER_MODEL=openai/gpt-5

# === Behavior ===
CASCADE_TIMEOUT_MS=6000
CASCADE_MIN_CHARS=200
CHAT_HISTORY_MAX=20
FREE_ANALYZE_LIMIT=1
HEALTH_MODE=strict
ALLOWED_ORIGINS=https://longopass.myideasoft.com

# Logging / retention
LOG_PROVIDER_RAW=true
RETENTION_DAYS=365

```
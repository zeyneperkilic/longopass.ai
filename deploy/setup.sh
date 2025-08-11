#!/bin/bash
# Longopass AI Deployment Script

set -e

echo "🚀 Setting up Longopass AI deployment..."

# Create data directory for persistence
echo "📁 Creating data directory..."
mkdir -p ./data

# Copy environment template if .env doesn't exist
if [ ! -f .env ]; then
    echo "📋 Creating .env from template..."
    echo "⚠️  Please edit .env with your OPENROUTER_API_KEY and domain settings"
    cat > .env << 'EOF'
# OpenRouter API Configuration - REQUIRED
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE

# Domain Configuration - Update with your domain
ALLOWED_ORIGINS=https://www.siteniz.com

# Model Configuration (Quality-first cascade)
CASCADE_MODELS=google/gemini-2.5-pro,x-ai/grok-2,deepseek/deepseek-r1,meta-llama/llama-3.1-8b-instruct
FINALIZER_MODEL=openai/gpt-5

# Health Guard Configuration
HEALTH_MODE=topic
MODERATION_MODEL=meta-llama/llama-3.1-8b-instruct
PRESCRIPTION_BLOCK=true

# Rate Limiting
DAILY_CHAT_LIMIT=100
FREE_ANALYZE_LIMIT=1

# System Configuration
CASCADE_TIMEOUT_MS=8000
CHAT_HISTORY_MAX=20
DB_PATH=/app/app.db
EOF
    echo "✅ .env file created. Please edit it before running docker-compose up!"
    exit 1
fi

# Build and start the container
echo "🐳 Building Docker container..."
docker-compose build

echo "▶️  Starting Longopass AI..."
docker-compose up -d

echo "⏳ Waiting for service to be ready..."
sleep 10

# Health check
echo "🏥 Checking service health..."
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "✅ Longopass AI is running successfully!"
    echo "📖 API docs: http://localhost:8000/docs"
    echo "🧪 Demo page: http://localhost:8000/static/index.html"
    echo "📜 Widget script: http://localhost:8000/widget.js"
else
    echo "❌ Service health check failed. Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Set up your domain (ai.siteniz.com) to point to this server"
echo "2. Configure SSL (see deploy/nginx.conf for example)"
echo "3. Update ALLOWED_ORIGINS in .env with your real domain"
echo "4. Add the widget script to your IdeaSoft site footer"
echo ""
echo "Widget embed code:"
echo "<script>"
echo "  window.LONGOPASS_AI_BASE = 'https://ai.siteniz.com';"
echo "  window.LONGOPASS_USER_ID = '';"
echo "  window.LONGOPASS_PLAN = 'premium';"
echo "</script>"
echo "<script src='https://ai.siteniz.com/widget.js' defer></script>"
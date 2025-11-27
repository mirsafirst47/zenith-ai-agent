#!/bin/bash

echo "🔌 Installing Real Service Integrations"
echo "======================================"

# Activate venv
source venv/bin/activate

echo "📦 Installing OpenAI (Whisper + GPT-4)..."
pip install openai==1.12.0

echo "📦 Installing ElevenLabs (TTS)..."
pip install elevenlabs==0.2.27

echo "📦 Installing Twilio (Phone + SMS)..."
pip install twilio==8.13.0

echo "📦 Installing SendGrid (Email)..."
pip install sendgrid==6.11.0

echo ""
echo "✅ All real services installed!"
echo ""
echo "🔧 Next steps:"
echo "1. Get API keys from:"
echo "   - OpenAI: https://platform.openai.com"
echo "   - ElevenLabs: https://elevenlabs.io"
echo "   - Twilio: https://twilio.com/console"
echo "   - SendGrid: https://sendgrid.com"
echo ""
echo "2. Update .env file:"
echo "   USE_REAL_OPENAI=true"
echo "   USE_REAL_TWILIO=true"
echo "   USE_REAL_ELEVENLABS=true"
echo "   OPENAI_API_KEY=sk-..."
echo "   TWILIO_ACCOUNT_SID=AC..."
echo "   etc."
echo ""
echo "3. Restart server:"
echo "   uvicorn app.main:app --reload"

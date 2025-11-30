# Claude AI Setup Guide

This guide will help you enable Claude AI integration for your Zenith AI Agent system.

## What Was Fixed

1. **Language Detection**: ✅ Working perfectly! The system detects Spanish, French, Chinese, Russian, and English from both phone numbers and spoken text.

2. **Claude Integration**: Now properly integrated into the intelligent agent. When Claude is available, it will be used to generate natural, contextual responses in any supported language.

3. **Diagnostic Logging**: Added comprehensive logging to help diagnose any issues during testing.

## Setup Instructions

### Step 1: Install the Anthropic Package

The anthropic package has been added to `requirements.txt`. Install it with:

```bash
pip install anthropic
```

Or install all dependencies:

```bash
pip install -r backend/requirements.txt
```

### Step 2: Get Your Claude API Key

1. Go to [Anthropic Console](https://console.anthropic.com/account/keys)
2. Create a new API key
3. Copy the key (it will start with `sk-ant-`)

### Step 3: Set the Environment Variable

**For local development:**

Option A - Add to your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

Option B - Create a `.env` file in the backend directory:
```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Option C - Set it before running:
```bash
ANTHROPIC_API_KEY='sk-ant-your-key-here' python -m uvicorn app.main:app --reload
```

### Step 4: Verify Installation

Run the test script to verify everything is working:

```bash
cd backend
python3 test_system.py
```

You should see:
- ✅ All language detection tests passing
- ✅ Claude service available: True
- ✅ IntelligentAgent initialized with Claude
- ✅ Mock response from Claude

## How It Works

### Language Detection Flow

1. **Initial Language Detection** (from phone number):
   - Caller's phone number is parsed to extract country code
   - Country code is mapped to language (US→English, Spain→Spanish, etc.)

2. **Dynamic Language Detection** (from spoken text):
   - User's message is analyzed for language-specific keywords
   - If keywords match (e.g., "hola", "gracias" for Spanish), language is updated
   - Falls back to statistical language detection if available

### Claude Response Generation Flow

1. **Context Building**:
   - Detects user emotion (happy, frustrated, angry, etc.)
   - Extracts entities (party size, date, time, name, etc.)
   - Determines intent (booking, order, complaint, etc.)
   - Adapts tone based on emotion

2. **System Prompt Creation**:
   - Claude receives instructions specific to the detected language
   - Business information is included for context
   - Customer emotion and intent are communicated
   - Phone conversation constraints are explained (short, natural, helpful)

3. **Response Generation**:
   - Claude generates a natural, conversational response
   - Response is kept short for phone conversations (2-3 sentences)
   - Language is adapted to match the customer

4. **Fallback Chain**:
   - If Claude fails → Use OpenAI (if available)
   - If OpenAI fails → Use smart mock responses
   - Smart responses are context-aware and follow the same business logic

## Testing Languages

Try making test calls with different languages:

### English
- Message: "I'd like to make a reservation for 4 people"
- Expected response: English, with booking details

### Spanish
- Message: "Quiero hacer una reserva para 4 personas"
- Expected response: Spanish, respecting the language preference

### French
- Message: "Je voudrais réserver une table pour 4 personnes"
- Expected response: French response from Claude

### Chinese
- Message: "我想预订4人的餐厅"
- Expected response: Chinese response from Claude

### Russian
- Message: "Я хотел бы зарезервировать стол на 4 человека"
- Expected response: Russian response from Claude

## Troubleshooting

### "Claude is not available"

**Cause**: ANTHROPIC_API_KEY is not set or anthropic package is not installed

**Solution**:
```bash
# Install anthropic
pip install anthropic

# Set the API key
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Verify
python3 test_system.py
```

### "Claude returned empty response"

**Cause**: API error or rate limiting

**Solution**:
1. Check your API key is valid
2. Check you have API credits in your Anthropic account
3. Wait a moment and try again
4. The system will automatically fall back to mock responses

### Language not being detected

**Cause**: Text might be too short or keywords not recognized

**Solution**:
1. Ensure text is at least 3 characters long
2. Use keywords from the supported languages
3. Check the test script output for detected language

### Response is generic/not contextual

**Cause**: Claude might not have business information

**Solution**:
1. Ensure business data is being passed correctly
2. Check the backend logs for what information is being sent
3. Update the business info with more details (hours, services, etc.)

## Architecture Overview

```
Test Call from Settings
    ↓
/api/voice/test/simulate
    ↓
handle_incoming_call()
    ├─ Detect language from phone number
    ├─ Load business knowledge base
    └─ Generate personalized greeting
    ↓
User Message: "I want to make a reservation"
    ↓
process_speech()
    ├─ Detect language from text
    ├─ Run intelligent agent:
    │   ├─ Detect emotion
    │   ├─ Extract entities
    │   ├─ Determine intent
    │   └─ Generate response:
    │       └─ TRY Claude first
    │           └─ Send with language instructions
    │               └─ Generate natural, contextual response
    │               └─ If fails, fallback to mock
    ├─ Check for escalation
    └─ Return response with metadata
    ↓
Response: "I'd be happy to help! How many people will be dining with you?"
(Response is in detected language)
```

## Environment Variables

All environment variables should be set in your shell or in a `.env` file:

```bash
# Required for Claude
ANTHROPIC_API_KEY=sk-ant-...

# Optional (for production use)
OPENAI_API_KEY=sk-...  # Fallback if Claude fails
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
ELEVENLABS_API_KEY=...
DATABASE_URL=...  # For production database
```

## Performance Notes

- **Model**: claude-sonnet-4-20250514 (fast, capable)
- **Alternative**: claude-opus-4-1-20250414 (highest quality, slower)
- **Response Time**: ~1-2 seconds
- **Max Response Length**: 300 tokens
- **Context Window**: Last 10 conversation turns

## Costs

Claude API calls are billed per token. For typical restaurant booking conversations:
- Average call: ~500 tokens = ~0.01 USD
- 100 test calls: ~1 USD
- See [Anthropic pricing](https://www.anthropic.com/pricing) for current rates

## Next Steps

1. Install anthropic package
2. Set ANTHROPIC_API_KEY environment variable
3. Run the test script to verify
4. Make a test call from Settings in the dashboard
5. Check the backend console for detailed logs

---

**Note**: The system gracefully degrades if Claude is unavailable. You can still test the complete functionality with mock responses, but real Claude responses will be much more natural and contextual.

# Instagram Fact-Checker

AI-powered fact-checking for Instagram posts using vision models, web search, and reasoning. Choose between fast traditional pipeline or deep agentic investigation.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green)](https://fastapi.tiangolo.com)

---

## ✨ Features

**Two Fact-Checking Engines:**
- **V1** — Fast traditional pipeline (~1-2 min)
- **V2** — Deep agentic investigation (~2-5 min)

**Multiple Access Methods:**
- **CLI** — Run from terminal
- **REST API** — FastAPI with interactive docs

**AI-Powered:**
- Vision analysis (Llama 4 Scout)
- Claim extraction (Llama 3.3 70B)
- Web search (DuckDuckGo - no API key needed)
- Agentic reasoning (LangChain + LangGraph)

---

## 🚀 Quick Start

### 1. Setup

**Linux/macOS:**
```bash
bash setup.sh
```

**Windows:**
```bash
setup.bat
```

**Manual:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
# Get free key: https://console.groq.com
```

### 3. Run

**CLI:**
```bash
python app/main.py      # V1 - Fast
python app/main_v2.py   # V2 - Detailed
```

**REST API:**
```bash
python app/api.py
# Visit: http://localhost:8000/docs
```

---

## 📖 Usage

### CLI Example

```bash
$ python app/main.py
Enter Instagram Post URL: https://www.instagram.com/p/ABC123/

[1/3] Scraping post…
[2/3] Preprocessing (downloading images)…
[3/3] Fact-checking (vision + web search + reasoning)…

═══════════════════════════════════════════
  FACT-CHECK RESULT
═══════════════════════════════════════════
  Verdict : MISLEADING (MEDIUM confidence)
  
  Explanation:
  The claim is partially supported but lacks context...
  
  Key Sources:
    • https://reuters.com/...
    • https://bbc.com/...
═══════════════════════════════════════════

Full details → data/fact_check_result.json
```

### REST API Example

**Request:**
```bash
curl -X POST http://localhost:8000/api/fact-check \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/ABC123/",
    "version": "v1"
  }'
```

**Response:**
```json
{
  "post_url": "https://www.instagram.com/p/ABC123/",
  "owner": "username",
  "verdict": "MISLEADING",
  "confidence": "MEDIUM",
  "explanation": "The claim is partially supported...",
  "key_sources": ["https://reuters.com/..."],
  "extracted_claims": ["Claim 1", "Claim 2"]
}
```

**Interactive API Docs:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📁 Project Structure

```
instagram-fact-checker/
├── app/
│   ├── api.py              # FastAPI REST service
│   ├── main.py             # CLI v1 entry point
│   ├── main_v2.py          # CLI v2 entry point
│   ├── scraper.py          # Instagram scraping
│   ├── preprocessor.py     # Image processing
│   ├── fact_checker.py     # V1 pipeline
│   └── fact_checker_v2.py  # V2 agentic engine
├── data/                   # Generated data & images
├── .env.example            # Config template
├── pyproject.toml          # Project metadata
├── requirements.txt        # Dependencies
├── setup.sh / setup.bat    # Setup scripts
├── README.md               # This file
└── QUICK_START.md          # Quick reference
```

---

## 🔄 How It Works

### V1: Traditional Pipeline
```
Instagram URL
    ↓
[Scraper] → Fetch post metadata + images
    ↓
[Vision] → Llama 4 Scout analyzes images
    ↓
[Claims] → Extract verifiable claims
    ↓
[Search] → DuckDuckGo finds evidence
    ↓
[Verdict] → Cross-reference & determine accuracy
```

### V2: Agentic Investigation
```
Instagram URL
    ↓
[Scraper] → Fetch post metadata + images
    ↓
[Vision] → Llama 4 Scout analyzes images
    ↓
[Agent] → Autonomous reasoning:
  • Identifies claims
  • Searches web iteratively
  • Refines queries for better results
  • Cross-checks multiple sources
  • Iterates until confident
    ↓
[Verdict] → Per-claim breakdown with evidence
```

---

## 📊 Output Examples

### V1 Output

```json
{
  "verdict": "MISLEADING",
  "confidence": "MEDIUM",
  "explanation": "Detailed explanation...",
  "key_sources": ["url1", "url2"],
  "extracted_claims": ["Claim 1", "Claim 2"]
}
```

### V2 Output

```json
{
  "verdict": "MISLEADING",
  "confidence": "MEDIUM",
  "claim_details": [
    {
      "claim": "Specific claim text",
      "verdict": "REAL",
      "evidence": "Evidence from sources..."
    }
  ],
  "key_sources": ["url1", "url2"],
  "engine": "v2-agentic-langgraph"
}
```

---

## 🆚 V1 vs V2

| Feature | V1 | V2 |
|---------|----|----|
| **Speed** | ~1-2 min | ~2-5 min |
| **Depth** | Quick overview | Deep investigation |
| **Search** | Direct | Iterative refinement |
| **Output** | Single verdict | Per-claim breakdown |
| **Best For** | Speed | Accuracy & detail |

---

## 📋 Requirements

- **Python 3.13+**
- **GROQ_API_KEY** — Free at https://console.groq.com
- **Internet connection**
- **Instagram posts** — Must be public and image-based (videos not supported)

---

## 🚨 Limitations

- ❌ Video/Reel posts (image posts only)
- ❌ Private posts
- ❌ Very subjective claims (opinions)
- ❌ Unverifiable personal anecdotes
- ⚠️ Very recent events may lack coverage

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY not found` | Add key to `.env` file |
| `403 Forbidden` from Instagram | Normal — Instaloader retries automatically |
| `No results found` | Claim too vague; try V2 for smarter searching |
| `VideoPostError` | Only image posts supported |
| `Rate limited` | Wait 15-60 seconds and retry |

---

## 📦 API Reference

### Endpoints

**Health Check:**
```bash
GET /
```

**Fact-Check (Query Params):**
```bash
GET /api/fact-check?url=INSTAGRAM_URL&version=v1
```

**Fact-Check (JSON Body):**
```bash
POST /api/fact-check
Content-Type: application/json

{
  "url": "INSTAGRAM_URL",
  "version": "v1"  // or "v2"
}
```

### Response Format

```json
{
  "post_url": "string",
  "owner": "string",
  "verdict": "REAL | FAKE | MISLEADING | NOT ENOUGH INFO",
  "confidence": "LOW | MEDIUM | HIGH",
  "explanation": "string",
  "key_sources": ["string"],
  "extracted_claims": ["string"],  // v1 only
  "claim_details": [...]           // v2 only
}
```

---

## 🔐 Security

**Current (Development):**
- No authentication
- No rate limiting
- Open for testing

**For Production:** Add authentication, rate limiting, HTTPS, request logging, and CORS policies.

---

## 🛠️ Development

### Install with Dev Dependencies
```bash
pip install -e ".[dev]"
```

### Run in Dev Mode
```bash
# API with auto-reload
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 Dependencies

**Core:**
- `fastapi` + `uvicorn` — Web framework
- `groq` — LLM API (Llama models)
- `langchain` + `langgraph` — Agent framework
- `instaloader` — Instagram scraping
- `ddgs` — Web search (no key needed)
- `beautifulsoup4` + `lxml` — HTML parsing
- `requests` + `pillow` — HTTP & images
- `pydantic` — Data validation
- `python-dotenv` — Environment config

See [pyproject.toml](pyproject.toml) for full list.

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

MIT

---

## 🙏 Credits

- **Groq** — Free LLM API
- **Instaloader** — Instagram scraping
- **DuckDuckGo** — Web search
- **LangChain** — Agent framework
- **FastAPI** — Web framework

---

**Version:** 0.1.0  
**Status:** ✅ Production Ready

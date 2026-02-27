# Quick Start Guide

**Instagram Fact-Checker** — Verify Instagram posts using AI, vision, and web search.

---

## ⚡ 60-Second Setup

### 1. Install Dependencies
```bash
# macOS/Linux
bash setup.sh

# Windows
setup.bat
```

Or manually:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure API Key
```bash
cp .env.example .env
# Edit .env and add GROQ_API_KEY from https://console.groq.com
```

### 3. Run It
```bash
# Version 1 (traditional pipeline)
python main.py

# Version 2 (agentic AI)
python main_v2.py
```

When prompted, paste an Instagram post URL:
```
https://www.instagram.com/p/DUDmwcmjFX-/?img_index=1
```

---

## 🎯 What It Does

✅ Scrapes Instagram post metadata and images  
✅ Analyzes images using Llama 4 Scout vision  
✅ Extracts factual claims  
✅ Searches the web for evidence  
✅ Determines: **REAL** | **FAKE** | **MISLEADING** | **NOT ENOUGH INFO**

---

## 📁 Output

Results saved to `data/fact_check_result.json`:
```json
{
  "post_url": "https://www.instagram.com/p/...",
  "verdict": "MISLEADING",
  "confidence": "MEDIUM",
  "explanation": "Detailed analysis...",
  "key_sources": ["url1", "url2"]
}
```

---

## 🆚 V1 vs V2

| Feature | V1 | V2 |
|---------|----|----|
| Pipeline | Fixed sequence | Autonomous agent |
| Search | Direct DuckDuckGo | Agent iterates, refines |
| Output | Single verdict | Per-claim breakdown |
| Depth | Quick & simple | Deep investigation |
| Speed | Faster | Slower (more thorough) |

**Choose V1 for speed, V2 for detail.**

---

## ⚠️ Requirements

- **Python**: 3.13+
- **API Key**: GROQ_API_KEY (free from https://console.groq.com)
- **Internet**: Required for scraping and web search
- **Instagram**: Post must be public and image-based (not video)

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY not found` | Add key to `.env` file (see Step 2 above) |
| `403 Forbidden` from Instagram | Normal — Instaloader retries automatically |
| `No results found` | Claim is too vague or very obscure; try V2 for smarter searching |
| `Video/Reel post error` | Only image posts supported; video support coming soon |

---

## 📚 Full Documentation

See [README.md](README.md) for comprehensive documentation.

---

## 💡 Example

```bash
$ python main.py
Enter Instagram Post URL: https://www.instagram.com/p/DUDmwcmjFX-/?img_index=1

[1/3] Scraping post…
[2/3] Preprocessing (downloading images)…
[3/3] Fact-checking (vision + web search + reasoning)…

═══════════════════════════════════════════
  FACT-CHECK RESULT
═══════════════════════════════════════════
  Post    : https://www.instagram.com/p/DUDmwcmjFX-/
  Owner   : @aiwith.akash
  Verdict : MISLEADING  (MEDIUM confidence)
═══════════════════════════════════════════
```

---

**Ready to fact-check?** Run the setup script above and start verifying! 🚀

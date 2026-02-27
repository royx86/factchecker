"""
fact_checker.py
---------------
Multimodal Instagram fact-checker.

Pipeline:
  1. Vision  → Llama 4 Scout describes each image, extracts info
  2. Claims  → Llama 3.3 70B extracts factual claims from caption + images
  3. Search  → DuckDuckGo finds web evidence for each claim
  4. Verdict → Llama 3.3 70B cross-references claims vs evidence

Requires:
  - GROQ_API_KEY in .env   (free at https://console.groq.com)
  - BING_API_KEY in .env    (optional, for reverse image search)
"""

import os
import sys
import json
import re
import base64
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from ddgs import DDGS
from bs4 import BeautifulSoup

# ============================================================
# CONFIG
# ============================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

if not GROQ_API_KEY:
    print("[Error] GROQ_API_KEY not found in .env file.")
    print("  1. Go to https://console.groq.com → API Keys → Create key")
    print("  2. Add to your .env file: GROQ_API_KEY=your_key_here")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"   # free, supports images
TEXT_MODEL   = "llama-3.3-70b-versatile"                     # free, strong reasoning

RESULT_PATH  = Path("data") / "fact_check_result.json"

TRUSTED_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com",
    ".gov", ".edu", "who.int", "un.org",
]


# ============================================================
# RATE-LIMIT RETRY WRAPPER
# ============================================================
def groq_call(fn, retries: int = 4):
    """Calls fn() with exponential back-off on Groq 429 errors."""
    wait = 15
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                print(f"  [FactChecker] Rate limited — waiting {wait}s "
                      f"(attempt {attempt}/{retries})…")
                time.sleep(wait)
                wait = min(wait * 2, 120)
            else:
                raise
    raise RuntimeError("Max retries exceeded — try again in a few minutes.")


# ============================================================
# IMAGE ENCODING
# ============================================================
def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ============================================================
# 1. VISION — describe each image & extract information
# ============================================================
def describe_images(local_image_paths: list[str]) -> list[str]:
    """Send each image to Llama 4 Scout vision model.
    Returns a list of detailed descriptions."""
    if not local_image_paths:
        print("  [FactChecker] No images to analyze.")
        return []

    descriptions = []
    for i, path in enumerate(local_image_paths, 1):
        print(f"  [FactChecker] Analyzing image {i}/{len(local_image_paths)}: {path}")
        try:
            b64 = encode_image(path)

            def call(b=b64):
                return client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b}"}
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Describe this image in detail. Focus on: "
                                    "people, objects, any visible text, location clues, "
                                    "events, dates, statistics, and anything that could "
                                    "be a factual claim. Extract all text visible in the image."
                                )
                            }
                        ]
                    }],
                    max_tokens=600
                )

            response = groq_call(call)
            desc = response.choices[0].message.content.strip()
            descriptions.append(desc)
            print(f"    → {desc[:120]}…")

        except Exception as e:
            print(f"  [FactChecker] Failed on image {i}: {e}")
            descriptions.append(f"[Image analysis failed: {e}]")

        # Pause between calls to stay under rate limits
        if i < len(local_image_paths):
            time.sleep(3)

    return descriptions


# ============================================================
# 2. CLAIM EXTRACTION (text model)
# ============================================================
def extract_claims(caption: str, image_descriptions: list[str]) -> list[str]:
    """Ask the LLM to list the key factual claims from the post."""
    combined = f"POST CAPTION:\n{caption or '(no caption)'}\n\nIMAGE DESCRIPTIONS:\n"
    for i, desc in enumerate(image_descriptions, 1):
        combined += f"Image {i}: {desc}\n\n"
    if not image_descriptions:
        combined += "(no images available)\n"

    prompt = (
        "You are given an Instagram post's caption and AI-generated descriptions of its images.\n"
        "Extract up to 5 specific, verifiable REAL-WORLD factual claims the post is making.\n\n"
        "Rules:\n"
        "- Focus on claims about events, people, statistics, dates, or facts — NOT visual details like clothing or accessories\n"
        "- State each claim as a standalone factual statement (e.g., 'India plays in the 2026 AFC Women's Asian Cup starting March 4th')\n"
        "- Do NOT describe what the image shows (e.g., avoid 'The woman is wearing earrings')\n"
        "- Do NOT start with 'The post says…' or 'The post mentions…'\n"
        "- If the post is primarily promotional or opinion-based with no verifiable facts, return 'NO VERIFIABLE CLAIMS'\n"
        "- Return each claim on its own numbered line, nothing else\n\n"
        + combined
    )

    def call():
        return client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )

    raw = groq_call(call).choices[0].message.content.strip()

    # Clean numbered list into plain strings, filter out LLM preamble
    lines = re.split(r"\n+", raw)
    skip_patterns = re.compile(
        r"(here are|below are|the following|factual claims|social.media post)",
        re.IGNORECASE
    )
    cleaned = []
    for line in lines:
        line = re.sub(r"^\d+[\).\s-]*", "", line).strip()
        line = re.sub(r"^\*+\s*", "", line).strip()   # strip markdown bold
        if len(line) > 10 and not skip_patterns.search(line):
            cleaned.append(line)

    claims = cleaned[:5]
    print(f"  [FactChecker] Extracted {len(claims)} claim(s).")
    return claims


# ============================================================
# 3. WEB SEARCH — DuckDuckGo (no API key needed)
# ============================================================
def search_web(query: str, max_results: int = 5) -> list[dict]:
    if not query or not query.strip():
        return []
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(
                query,
                region="wt-wt",
                safesearch="moderate",
                max_results=max_results,
            ):
                results.append({
                    "title": r.get("title", ""),
                    "href":  r.get("href", ""),
                    "body":  r.get("body", ""),
                })
    except Exception as e:
        print(f"  [Search Error] {e}")
    return results


def fetch_article(url: str) -> str:
    """Try to grab the article text from a URL."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                            timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text[:3000]
    except Exception:
        return ""


def credibility_score(url: str) -> int:
    """Simple heuristic: 2 for trusted sources, 1 otherwise."""
    for domain in TRUSTED_DOMAINS:
        if domain in url:
            return 2
    return 1


def gather_evidence(claims: list[str]) -> str:
    """Search the web for each claim, fetch articles, build evidence block."""
    evidence_text = ""
    for claim in claims:
        query = claim.strip()[:120]
        print(f"  [FactChecker] Searching: {query}")
        results = search_web(query, max_results=4)

        if not results:
            print(f"  [FactChecker] No results for: {query[:60]}")
            evidence_text += f"NO RESULTS FOUND FOR CLAIM: {claim}\n\n"
            continue

        for r in results:
            url     = r.get("href", "")
            snippet = r.get("body", "")
            title   = r.get("title", "")
            if not url:
                continue

            # Try full article; fall back to search snippet
            article = fetch_article(url)
            content = article if len(article) >= 100 else snippet

            score = credibility_score(url)
            evidence_text += (
                f"SOURCE: {url}\n"
                f"TITLE:  {title}\n"
                f"CREDIBILITY: {'HIGH' if score == 2 else 'NORMAL'}\n"
                f"CONTENT: {content[:1500]}\n\n"
            )
    return evidence_text


# ============================================================
# 3b. REVERSE IMAGE SEARCH (Bing — optional)
# ============================================================
def reverse_image_search(image_path: str) -> list[str]:
    if not BING_API_KEY:
        return []
    endpoint = "https://api.bing.microsoft.com/v7.0/images/visualsearch"
    headers  = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(endpoint, headers=headers,
                                 files={"image": f})
        if resp.status_code != 200:
            return []
        data    = resp.json()
        matches = []
        for tag in data.get("tags", []):
            for action in tag.get("actions", []):
                for item in action.get("data", {}).get("value", []):
                    if "hostPageUrl" in item:
                        matches.append(item["hostPageUrl"])
        return list(set(matches))[:10]
    except Exception:
        return []


# ============================================================
# 4. FINAL VERDICT (text model cross-references claims vs evidence)
# ============================================================
def get_verdict(caption: str, claims: list[str], evidence: str) -> dict:
    if not claims:
        return {
            "verdict":     "NOT ENOUGH INFO",
            "confidence":  "HIGH",
            "explanation": "No clear factual claims detected in this post.",
            "key_sources": [],
        }

    if not evidence.strip():
        return {
            "verdict":     "NOT ENOUGH INFO",
            "confidence":  "LOW",
            "explanation": "Web search returned no usable evidence.",
            "key_sources": [],
        }

    claims_str = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))

    prompt = f"""You are a professional investigative fact-checker.

POST CAPTION:
{caption or "(no caption)"}

CLAIMS TO VERIFY:
{claims_str}

EVIDENCE FROM THE WEB:
{evidence}

Cross-reference each claim against the evidence.
Return STRICT JSON only — no extra text, no markdown:
{{
  "verdict": "REAL | FAKE | MISLEADING | NOT ENOUGH INFO",
  "confidence": "LOW | MEDIUM | HIGH",
  "explanation": "2-3 sentences citing specific sources that support or contradict each claim.",
  "key_sources": ["url1", "url2"]
}}
"""

    def call():
        return client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900
        )

    raw = groq_call(call).choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())

            # Handle per-claim format: {"claims": [...]}
            if "claims" in parsed and isinstance(parsed["claims"], list):
                verdicts = [c.get("verdict", "").upper() for c in parsed["claims"]]
                if any(v == "FAKE" for v in verdicts):
                    overall = "FAKE"
                elif any(v == "MISLEADING" for v in verdicts):
                    overall = "MISLEADING"
                elif all(v == "REAL" for v in verdicts):
                    overall = "REAL"
                else:
                    overall = "MISLEADING" if any(v == "FAKE" for v in verdicts) else "NOT ENOUGH INFO"

                explanations = []
                sources = []
                for c in parsed["claims"]:
                    v = c.get("verdict", "")
                    expl = c.get("explanation", "")
                    claim_text = c.get("claim", "")
                    explanations.append(f"[{v}] {claim_text}: {expl}")
                    sources.extend(c.get("key_sources", []))

                return {
                    "verdict":     overall,
                    "confidence":  "MEDIUM",
                    "explanation": " | ".join(explanations),
                    "key_sources": list(dict.fromkeys(sources))[:5],
                }

            # Standard single-verdict format
            if "verdict" in parsed:
                return parsed

        except json.JSONDecodeError:
            pass

    # Fallback if model didn't return valid JSON
    return {
        "verdict":     "NOT ENOUGH INFO",
        "confidence":  "LOW",
        "explanation": raw,
        "key_sources": [],
    }


# ============================================================
# MAIN PIPELINE
# ============================================================
def run(preprocessed: dict) -> dict:
    """
    Full fact-check pipeline:
      1. Vision analysis  — extract info from images
      2. Claim extraction — identify factual claims
      3. Web search       — gather evidence per claim
      4. Reverse image    — check image origin (if Bing key)
      5. Verdict          — LLM cross-references everything
    """
    caption = preprocessed.get("caption", "")
    images  = preprocessed.get("local_images", [])

    # ── Step 1: Analyze images ──────────────────────────────
    print("\n[FactChecker] Step 1 — Analyzing images with Llama 4 Scout Vision…")
    image_descriptions = describe_images(images)

    # ── Step 2: Extract claims ──────────────────────────────
    print("\n[FactChecker] Step 2 — Extracting factual claims…")
    claims = extract_claims(caption, image_descriptions)
    for i, c in enumerate(claims, 1):
        print(f"    {i}. {c}")

    # ── Step 3: Web evidence ────────────────────────────────
    print("\n[FactChecker] Step 3 — Searching the web for evidence…")
    evidence = gather_evidence(claims)
    print(f"  [FactChecker] Evidence collected: {len(evidence)} chars")

    # ── Step 4: Reverse image search (optional) ─────────────
    print("\n[FactChecker] Step 4 — Reverse image search…")
    for img in images:
        for url in reverse_image_search(img):
            evidence += f"REVERSE_IMAGE_MATCH: {url}\n"
    if not BING_API_KEY:
        print("  [FactChecker] Skipped (no BING_API_KEY).")

    # ── Step 5: Final verdict ───────────────────────────────
    print("\n[FactChecker] Step 5 — Final reasoning (70B)…")
    verdict_data = get_verdict(caption, claims, evidence)

    # ── Build result ────────────────────────────────────────
    result = {
        "post_url":           preprocessed.get("url"),
        "owner":              preprocessed.get("owner_username"),
        "caption":            caption,
        "image_descriptions": image_descriptions,
        "extracted_claims":   claims,
        "verdict":            verdict_data.get("verdict"),
        "confidence":         verdict_data.get("confidence"),
        "explanation":        verdict_data.get("explanation"),
        "key_sources":        verdict_data.get("key_sources", []),
    }

    # Save to disk
    RESULT_PATH.parent.mkdir(exist_ok=True)
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=4)
    print(f"\n[FactChecker] Result saved → {RESULT_PATH}")

    return result
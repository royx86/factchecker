"""
fact_checker_v2.py
------------------
Agentic fact-checker using LangChain + LangGraph.

Key improvement over v1:
  - An autonomous ReAct agent decides WHAT to search, can refine
    queries, cross-check multiple sources, and iterate until confident.
  - The agent has tools: web_search, read_article.
  - It reasons step-by-step instead of following a fixed pipeline.

Requires:  GROQ_API_KEY in .env
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
from bs4 import BeautifulSoup
from ddgs import DDGS

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# ============================================================
# CONFIG
# ============================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[Error] GROQ_API_KEY not found in .env file.")
    sys.exit(1)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL   = "llama-3.3-70b-versatile"
RESULT_PATH  = Path("data") / "fact_check_result.json"

# LangChain LLMs
reasoning_llm = ChatGroq(
    model=TEXT_MODEL,
    api_key=GROQ_API_KEY,
    temperature=0,
    max_tokens=1024,
)

vision_llm = ChatGroq(
    model=VISION_MODEL,
    api_key=GROQ_API_KEY,
    temperature=0,
    max_tokens=600,
)

TRUSTED_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    ".gov", ".edu", "who.int", "un.org",
    "snopes.com", "factcheck.org", "politifact.com",
    "altnews.in", "boomlive.in",
]


# ============================================================
# RATE-LIMIT WRAPPER
# ============================================================
def with_retry(fn, retries=4):
    wait = 15
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                print(f"  [Agent] Rate limited — waiting {wait}s "
                      f"(attempt {attempt}/{retries})…")
                time.sleep(wait)
                wait = min(wait * 2, 120)
            else:
                raise
    raise RuntimeError("Max retries exceeded.")


# ============================================================
# VISION — analyze images before handing off to the agent
# ============================================================
def analyze_image(image_path: str) -> str:
    """Use Llama 4 Scout to describe an image and extract info."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    def call():
        return vision_llm.invoke([
            HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                },
                {
                    "type": "text",
                    "text": (
                        "Describe this image in detail. Extract ALL visible text. "
                        "Note people, objects, events, dates, statistics, location "
                        "clues, and anything that could be a factual claim."
                    )
                }
            ])
        ])

    resp = with_retry(call)
    return resp.content.strip()


# ============================================================
# AGENT TOOLS
# ============================================================

@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Use specific, focused queries
    to find evidence for or against a factual claim. Try different
    phrasings if initial results are poor."""
    print(f"  [Tool] web_search: {query}")
    if not query or not query.strip():
        return "Empty query — please provide a search term."
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(
                query.strip(),
                region="wt-wt",
                safesearch="moderate",
                max_results=5,
            ):
                results.append(r)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return "No results found. Try a different query."

    output = ""
    for r in results:
        url   = r.get("href", "")
        trust = "TRUSTED" if any(d in url for d in TRUSTED_DOMAINS) else "unknown"
        output += (
            f"TITLE: {r.get('title', '')}\n"
            f"URL: {url} [{trust}]\n"
            f"SNIPPET: {r.get('body', '')}\n\n"
        )
    return output


@tool
def read_article(url: str) -> str:
    """Fetch and read the full text of a web article. Use this when a
    search snippet is promising but you need more detail to verify a claim."""
    print(f"  [Tool] read_article: {url}")
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        if len(text) < 50:
            return "Could not extract meaningful article text."
        return text[:4000]
    except Exception as e:
        return f"Failed to fetch article: {e}"


# ============================================================
# SYSTEM PROMPT — the agent's fact-checking persona
# ============================================================
SYSTEM_PROMPT = """You are an expert investigative fact-checker agent.

You receive an Instagram post (caption + image descriptions) and must determine its factual accuracy.

YOUR PROCESS:
1. Identify the key VERIFIABLE factual claims (not opinions, not image descriptions).
2. For EACH claim, use web_search with a specific, focused query.
3. If a search result looks promising, use read_article to read the full text.
4. Cross-reference claims against MULTIPLE sources when possible.
5. Results marked [TRUSTED] are from established news/fact-check organizations — prefer these.
6. If initial searches are inconclusive, TRY DIFFERENT QUERIES (rephrase, add dates, names).

RULES:
- Search for EACH claim SEPARATELY — don't combine them.
- Try at least 2 different search queries per claim if the first isn't conclusive.
- Keep searching until you're confident in each claim's accuracy.
- Be specific in your search queries (include names, dates, numbers).

WHEN YOU'RE DONE, output your verdict in this EXACT JSON format:
```json
{
  "verdict": "REAL or FAKE or MISLEADING or NOT ENOUGH INFO",
  "confidence": "LOW or MEDIUM or HIGH",
  "claims": [
    {
      "claim": "the specific claim text",
      "verdict": "REAL or FAKE or MISLEADING or NOT ENOUGH INFO",
      "evidence": "what you found, citing specific source URLs"
    }
  ],
  "explanation": "Overall 2-3 sentence summary.",
  "key_sources": ["url1", "url2", "url3"]
}
```"""


# ============================================================
# BUILD THE REACT AGENT
# ============================================================
def build_agent():
    tools = [web_search, read_article]
    agent = create_react_agent(
        model=reasoning_llm,
        tools=tools,
    )
    return agent


# ============================================================
# MAIN PIPELINE
# ============================================================
def run(preprocessed: dict) -> dict:
    """
    Agentic fact-check pipeline (v2):
      1. Vision analysis — extract info from images (pre-agent)
      2. Agent takes over — autonomously searches, reads, reasons
      3. Agent returns structured verdict
    """
    caption = preprocessed.get("caption", "")
    images  = preprocessed.get("local_images", [])

    # ── Step 1: Analyze images ───────────────────────────────
    print("\n[Agent v2] Step 1 — Analyzing images with Llama 4 Scout Vision…")
    image_descriptions = []
    for i, path in enumerate(images, 1):
        print(f"  Analyzing image {i}/{len(images)}: {path}")
        try:
            desc = analyze_image(path)
            image_descriptions.append(desc)
            print(f"    → {desc[:100]}…")
        except Exception as e:
            print(f"    → Failed: {e}")
            image_descriptions.append(f"[Image analysis failed: {e}]")
        if i < len(images):
            time.sleep(3)

    # ── Step 2: Build context for the agent ──────────────────
    context = f"POST CAPTION:\n{caption or '(no caption)'}\n\n"
    if image_descriptions:
        context += "IMAGE DESCRIPTIONS:\n"
        for i, desc in enumerate(image_descriptions, 1):
            context += f"Image {i}: {desc}\n\n"
    else:
        context += "(No images in this post)\n"

    context += (
        f"\nPOST URL: {preprocessed.get('url', 'unknown')}\n"
        f"POSTED BY: @{preprocessed.get('owner_username', 'unknown')}\n"
        f"TIMESTAMP: {preprocessed.get('timestamp', 'unknown')}\n"
        f"LIKES: {preprocessed.get('likes', '?')}\n"
    )

    # ── Step 3: Run the agent ────────────────────────────────
    print("\n[Agent v2] Step 2 — Agent investigating (autonomous search + reasoning)…\n")
    agent = build_agent()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            "Fact-check this Instagram post. Identify claims, search for "
            "evidence, and provide your verdict.\n\n" + context
        )),
    ]

    try:
        response = agent.invoke(
            {"messages": messages},
            config={"recursion_limit": 40},
        )
        final_msg = response["messages"][-1].content
    except Exception as e:
        print(f"  [Agent v2] Agent error: {e}")
        final_msg = ""

    # ── Step 4: Parse verdict ────────────────────────────────
    print("\n[Agent v2] Step 3 — Parsing verdict…")
    verdict_data = parse_verdict(final_msg)

    # ── Build result ─────────────────────────────────────────
    result = {
        "post_url":           preprocessed.get("url"),
        "owner":              preprocessed.get("owner_username"),
        "caption":            caption,
        "image_descriptions": image_descriptions,
        "extracted_claims":   [c.get("claim", "") for c in verdict_data.get("claims", [])],
        "verdict":            verdict_data.get("verdict", "NOT ENOUGH INFO"),
        "confidence":         verdict_data.get("confidence", "LOW"),
        "explanation":        verdict_data.get("explanation", ""),
        "key_sources":        verdict_data.get("key_sources", []),
        "claim_details":      verdict_data.get("claims", []),
        "engine":             "v2-agentic-langgraph",
    }

    RESULT_PATH.parent.mkdir(exist_ok=True)
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=4)
    print(f"\n[Agent v2] Result saved → {RESULT_PATH}")

    return result


# ============================================================
# PARSE AGENT OUTPUT
# ============================================================
def parse_verdict(text: str) -> dict:
    if not text:
        return _fallback("Agent returned empty response.")

    cleaned = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if "verdict" in data:
                return data
        except json.JSONDecodeError:
            pass

    return _fallback(text)


def _fallback(text: str) -> dict:
    return {
        "verdict":     "NOT ENOUGH INFO",
        "confidence":  "LOW",
        "explanation": text[:500] if text else "Could not parse verdict.",
        "claims":      [],
        "key_sources": [],
    }

"""
main.py
-------
Entry point for the Instagram Fact-Checker.

Flow:
  1. User provides an Instagram post URL
  2. Scraper   → fetches post metadata + media URLs via Instaloader
  3. Preprocessor → downloads images locally, saves structured data
  4. FactChecker  → vision AI analyzes images, extracts claims from
                    text, searches internet for context, determines accuracy
"""

import sys
import scraper
import preprocessor
import fact_checker


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║      Instagram Post Fact-Checker         ║
║   Scrape → Analyze → Search → Verdict    ║
╚══════════════════════════════════════════╝
""")


def print_result(result: dict):
    verdict     = result.get("verdict", "UNKNOWN")
    confidence  = result.get("confidence", "?")
    explanation = result.get("explanation", "")
    sources     = result.get("key_sources", [])
    claims      = result.get("extracted_claims", [])

    # Terminal color codes
    colors = {
        "REAL":            "\033[92m",  # green
        "FAKE":            "\033[91m",  # red
        "MISLEADING":      "\033[93m",  # yellow
        "NOT ENOUGH INFO": "\033[94m",  # blue
    }
    reset = "\033[0m"
    color = colors.get(verdict, "\033[97m")

    print("\n" + "═" * 55)
    print("  FACT-CHECK RESULT")
    print("═" * 55)
    print(f"  Post    : {result.get('post_url')}")
    print(f"  Owner   : @{result.get('owner')}")
    print(f"  Verdict : {color}{verdict}{reset}  ({confidence} confidence)")

    if claims:
        print("\n  Claims verified:")
        for i, c in enumerate(claims, 1):
            print(f"    {i}. {c}")

    print(f"\n  Explanation:\n  {explanation}")

    if sources:
        print("\n  Key Sources:")
        for s in sources:
            print(f"    • {s}")

    print("═" * 55)
    print("  Full details → data/fact_check_result.json")
    print("═" * 55 + "\n")


def main():
    print_banner()

    # ── Step 1: Get URL from user ──────────────────────────
    url = input("Enter Instagram Post URL: ").strip()
    if not url:
        print("[Error] No URL provided. Exiting.")
        sys.exit(1)

    # ── Step 2: Scrape the post ────────────────────────────
    print("\n[1/3] Scraping post…\n")
    try:
        post_data = scraper.scrape(url)
    except scraper.VideoPostError as e:
        print(f"\n\033[93m⚠  {e}\033[0m\n")
        sys.exit(0)
    except Exception as e:
        print(f"[Error] Scraping failed: {e}")
        sys.exit(1)

    # ── Step 3: Preprocess (download images, save data) ───
    print("\n[2/3] Preprocessing (downloading images)…\n")
    try:
        preprocessed = preprocessor.preprocess(post_data)
    except Exception as e:
        print(f"[Error] Preprocessing failed: {e}")
        sys.exit(1)

    # ── Step 4: Fact-check ─────────────────────────────────
    print("\n[3/3] Fact-checking (vision + web search + reasoning)…\n")
    try:
        result = fact_checker.run(preprocessed)
    except Exception as e:
        print(f"[Error] Fact-checking failed: {e}")
        sys.exit(1)

    # ── Print final result ─────────────────────────────────
    print_result(result)


if __name__ == "__main__":
    main()
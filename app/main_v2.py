"""
main_v2.py
----------
Entry point for the Agentic Instagram Fact-Checker (v2).

Uses LangChain + LangGraph ReAct agent for autonomous investigation.
Run:  python main_v2.py
"""

import sys
import scraper
import preprocessor
import fact_checker_v2 as fact_checker


def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║   Instagram Fact-Checker  v2  (Agentic AI)   ║
║   Scrape → Vision → Agent Investigates       ║
╚══════════════════════════════════════════════╝
""")


def print_result(result: dict):
    verdict     = result.get("verdict", "UNKNOWN")
    confidence  = result.get("confidence", "?")
    explanation = result.get("explanation", "")
    sources     = result.get("key_sources", [])
    claims      = result.get("claim_details", [])

    colors = {
        "REAL":            "\033[92m",
        "FAKE":            "\033[91m",
        "MISLEADING":      "\033[93m",
        "NOT ENOUGH INFO": "\033[94m",
    }
    reset = "\033[0m"
    color = colors.get(verdict, "\033[97m")

    print("\n" + "═" * 60)
    print("  FACT-CHECK RESULT  (v2 — Agentic AI)")
    print("═" * 60)
    print(f"  Post    : {result.get('post_url')}")
    print(f"  Owner   : @{result.get('owner')}")
    print(f"  Verdict : {color}{verdict}{reset}  ({confidence} confidence)")

    if claims:
        print("\n  Per-claim breakdown:")
        for i, c in enumerate(claims, 1):
            cv = c.get("verdict", "?")
            cc = colors.get(cv, "\033[97m")
            print(f"    {i}. {cc}{cv}{reset} — {c.get('claim', '')}")
            evidence = c.get("evidence", "")
            if evidence:
                print(f"       Evidence: {evidence[:150]}…" if len(evidence) > 150 else f"       Evidence: {evidence}")

    print(f"\n  Explanation:\n  {explanation}")

    if sources:
        print("\n  Key Sources:")
        for s in sources:
            print(f"    • {s}")

    print("═" * 60)
    print("  Full details → data/fact_check_result.json")
    print("═" * 60 + "\n")


def main():
    print_banner()

    url = input("Enter Instagram Post URL: ").strip()
    if not url:
        print("[Error] No URL provided. Exiting.")
        sys.exit(1)

    # ── Scrape ──────────────────────────────────────────────
    print("\n[1/3] Scraping post…\n")
    try:
        post_data = scraper.scrape(url)
    except scraper.VideoPostError as e:
        print(f"\n\033[93m⚠  {e}\033[0m\n")
        sys.exit(0)
    except Exception as e:
        print(f"[Error] Scraping failed: {e}")
        sys.exit(1)

    # ── Preprocess ──────────────────────────────────────────
    print("\n[2/3] Preprocessing (downloading images)…\n")
    try:
        preprocessed = preprocessor.preprocess(post_data)
    except Exception as e:
        print(f"[Error] Preprocessing failed: {e}")
        sys.exit(1)

    # ── Agentic Fact-check ──────────────────────────────────
    print("\n[3/3] Agentic fact-checking (agent will search autonomously)…\n")
    try:
        result = fact_checker.run(preprocessed)
    except Exception as e:
        print(f"[Error] Fact-checking failed: {e}")
        sys.exit(1)

    print_result(result)


if __name__ == "__main__":
    main()

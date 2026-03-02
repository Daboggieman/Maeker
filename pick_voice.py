"""
pick_voice.py
-------------
Queries ElevenLabs for bold male narrative/storytelling voices,
displays a numbered list, and returns the chosen voice name via stdout.

Usage (called by run_job.bat):
    python pick_voice.py
    -> prints CHOSEN_VOICE=<voice_name>  on success
    -> prints CHOSEN_VOICE=George        on fallback / error
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Keywords that suggest a bold/narrative male voice
NARRATIVE_KEYWORDS = [
    "narrative", "narration", "storytelling", "story", "documentary",
    "deep", "bold", "powerful", "dramatic", "cinematic", "broadcast",
    "authoritative", "baritone", "resonant", "commanding", "epic",
    "announcer", "news", "rich", "gravelly", "intense", "heroic",
]

# Labels ElevenLabs uses for gender
MALE_LABELS = ["male"]


def score_voice(voice: dict) -> int:
    """Score a voice by how well it fits bold male narrative style."""
    score = 0
    labels = voice.get("labels", {})
    description = (
        labels.get("description", "") + " " +
        labels.get("use_case", "") + " " +
        labels.get("accent", "") + " " +
        voice.get("name", "")
    ).lower()

    gender = labels.get("gender", "").lower()
    if gender in MALE_LABELS:
        score += 10  # strong bonus for confirmed male
    elif gender and gender not in MALE_LABELS:
        score -= 20  # penalise confirmed non-male

    for kw in NARRATIVE_KEYWORDS:
        if kw in description:
            score += 3

    return score


def fetch_voices() -> list[dict]:
    """Fetch all available voices from ElevenLabs."""
    if not ELEVENLABS_API_KEY:
        print("[ERROR] ELEVENLABS_API_KEY not found in .env", file=sys.stderr)
        return []

    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[ERROR] ElevenLabs API returned {resp.status_code}", file=sys.stderr)
            return []
        return resp.json().get("voices", [])
    except Exception as exc:
        print(f"[ERROR] Could not reach ElevenLabs: {exc}", file=sys.stderr)
        return []


def main():
    print()
    print("  Fetching voices from ElevenLabs... please wait.")
    print()

    all_voices = fetch_voices()

    if not all_voices:
        print("CHOSEN_VOICE=George")
        return

    # Score and sort; keep top 50
    scored = sorted(all_voices, key=score_voice, reverse=True)[:50]

    if not scored:
        print("CHOSEN_VOICE=George")
        return

    # Display
    print("  ============================================================")
    print("   AVAILABLE VOICES  (Bold Male Narrative — Top 50)")
    print("  ============================================================")
    for i, v in enumerate(scored, start=1):
        labels    = v.get("labels", {})
        gender    = labels.get("gender", "unknown").title()
        accent    = labels.get("accent", "")
        use_case  = labels.get("use_case", labels.get("description", ""))
        accent_str = f"  [{accent}]" if accent else ""
        use_str    = f"  — {use_case}" if use_case else ""
        print(f"   {i:>2}. {v['name']:<28} {gender:<7}{accent_str}{use_str}")

    print("  ============================================================")
    print()

    # Prompt loop
    while True:
        raw = input("  Enter the number of your chosen voice: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(scored):
                chosen = scored[idx - 1]["name"]
                print()
                print(f"  >> Selected: {chosen}")
                print()
                # The bat file captures this line
                print(f"CHOSEN_VOICE={chosen}")
                return
        print(f"  [!] Please enter a number between 1 and {len(scored)}.")


if __name__ == "__main__":
    main()

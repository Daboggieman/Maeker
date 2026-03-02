import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Keywords that suggest a bold/narrative male voice quality
NARRATIVE_KEYWORDS = [
    "narrative", "narration", "storytelling", "story", "documentary",
    "deep", "bold", "powerful", "dramatic", "cinematic", "broadcast",
    "authoritative", "baritone", "resonant", "commanding", "epic",
    "announcer", "news", "rich", "gravelly", "intense", "heroic",
]

MALE_LABELS = {"male"}


def score_voice(voice: dict) -> int:
    """Score a voice by how well it fits bold male narrative style."""
    labels: dict[str, str] = voice.get("labels", {})
    description = " ".join([
        labels.get("description", ""),
        labels.get("use_case", ""),
        labels.get("accent", ""),
        voice.get("name", ""),
    ]).lower()

    score: int = 0
    gender = labels.get("gender", "").lower()
    if gender in MALE_LABELS:
        score += 10
    elif gender and gender not in MALE_LABELS:
        score -= 20

    keyword_score: int = sum(3 for kw in NARRATIVE_KEYWORDS if kw in description)

    return score + keyword_score


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Path to write chosen voice name")
    args = parser.parse_args()

    print()
    print("  Fetching voices from ElevenLabs... please wait.")

    all_voices = fetch_voices()

    FALLBACK = "George"

    if not all_voices:
        print(f"  [WARN] Could not fetch voices. Falling back to '{FALLBACK}'.")
        with open(args.out, "w") as f:
            f.write(FALLBACK)
        return

    # Score, sort, take top 50
    scored: list[dict] = sorted(all_voices, key=score_voice, reverse=True)[:50]  # type: ignore[misc]

    print()
    print("  ============================================================")
    print("   AVAILABLE VOICES  (Bold Male Narrative — Top 50)")
    print("  ============================================================")
    for i, v in enumerate(scored, start=1):
        labels   = v.get("labels", {})
        gender   = labels.get("gender", "unknown").title()
        accent   = labels.get("accent", "")
        use_case = labels.get("use_case", labels.get("description", ""))
        accent_str = f"  [{accent}]" if accent else ""
        use_str    = f"  — {use_case}" if use_case else ""
        print(f"   {i:>2}. {v['name']:<28} {gender:<8}{accent_str}{use_str}")

    print("  ============================================================")
    print()

    while True:
        try:
            raw = input("  Enter the number of your chosen voice: ").strip()
        except (EOFError, KeyboardInterrupt):
            chosen = FALLBACK
            break

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(scored):
                full_name  = scored[idx - 1]["name"]
                # ElevenLabs API names are the part before any ' - ' suffix
                api_name   = full_name.split(" - ")[0].strip()
                print()
                print(f"  >> Selected: {full_name}")
                print()
                chosen = api_name
                break
        print(f"  [!] Please enter a number between 1 and {len(scored)}.")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(chosen)


if __name__ == "__main__":
    main()

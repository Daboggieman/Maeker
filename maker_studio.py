import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from manager import JobManager

def main():
    parser = argparse.ArgumentParser(description="Maker Studio Orchestrator")
    parser.add_argument("--topic", help="Topic for the content")
    parser.add_argument("--category", default="General", help="Category of the content")
    parser.add_argument("--voice", default=None, help="ElevenLabs voice name to use for narration")
    parser.add_argument("--produce", action="store_true", help="Enable voice and video production")
    parser.add_argument("--webhook", help="URL for progress notifications")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    if not args.topic:
        print("Error: --topic is required.")
        sys.exit(1)

    # Initialize JobManager
    manager = JobManager(webhook_url=args.webhook)

    # Run the Job
    result = asyncio.run(manager.run_job(args.topic, args.category, produce=args.produce, voice=args.voice))

    # Output results
    if args.json:
        import json
        print(json.dumps(result, indent=4, default=str))
    else:
        if result.get("status") == "Error":
            print(f"\nCRITICAL ERROR: {result.get('message')}")
            sys.exit(1)
        else:
            print(f"\n--- JOB COMPLETE: {args.topic} ---")
            print(f"Status: {result.get('status')}")

if __name__ == "__main__":
    main()
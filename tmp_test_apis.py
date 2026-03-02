import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_elevenlabs():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    print(f"Testing ElevenLabs Key (Length: {len(api_key)})")
    headers = {"xi-api-key": api_key}
    try:
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
        print(f"ElevenLabs Response Code: {response.status_code}")
        if response.status_code == 200:
            print("Voices found:", [v['name'] for v in response.json().get('voices', [])[:5]])
        else:
            print("Error message:", response.text)
    except Exception as e:
        print(f"ElevenLabs Test Failed: {e}")

def test_pollinations():
    # Try the main domain instead of image.pollinations.ai
    proxies = ["https://pollinations.ai/p/test", "https://image.pollinations.ai/prompt/test"]
    for url in proxies:
        print(f"Testing Pollinations URL: {url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"Status: {r.status_code}, Content-Type: {r.headers.get('content-type')}")
        except Exception as e:
            print(f"Request Error: {e}")

if __name__ == "__main__":
    test_elevenlabs()
    print("-" * 20)
    test_pollinations()

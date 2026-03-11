"""
tiktok_uploader.py — Uploads videos to TikTok via pyktok (cookie-based session).

One-time setup
--------------
1. pip install pyktok playwright
2. playwright install chromium
3. Run: python tiktok_uploader.py --setup
   This opens a browser, you log in to TikTok, cookies are saved to tiktok_cookies.json.
4. Subsequent uploads use the saved cookies automatically — no manual login needed.
"""
import os
import sys
import argparse
from dotenv import load_dotenv  # type: ignore

load_dotenv()

COOKIES_PATH = os.getenv("TIKTOK_COOKIES_PATH", "tiktok_cookies.json")


class TikTokUploader:
    def __init__(self):
        self.cookies_path = COOKIES_PATH
        self._client = None

    def _get_client(self):
        """Lazy-initialise the pyktok/playwright session."""
        if self._client:
            return self._client
        try:
            import pyktok as pyk  # type: ignore
            pyk.specify_browser("chromium")
            if os.path.exists(self.cookies_path):
                # pyktok uses browser cookies automatically — just verify file exists
                print(f"[TikTok] Using saved session from: {self.cookies_path}")
            else:
                print(
                    "[TikTok] ERROR: No TikTok session found.\n"
                    "  Run: python tiktok_uploader.py --setup\n"
                    "  This will open a browser for you to log in once."
                )
                return None
            self._client = pyk
            return self._client
        except ImportError:
            print(
                "[TikTok] ERROR: pyktok is not installed.\n"
                "  Run: pip install pyktok playwright && playwright install chromium"
            )
            return None

    def setup_session(self):
        """Opens a browser for one-time TikTok login and saves session cookies."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            print("ERROR: Install playwright first: pip install playwright && playwright install chromium")
            return False

        print("\n[TikTok Setup] Opening browser — please log in to TikTok...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.tiktok.com/login")
            print("[TikTok Setup] Log in and then press ENTER here to save your session...")
            input()
            cookies = context.cookies()
            import json
            with open(self.cookies_path, "w") as f:
                json.dump(cookies, f, indent=2)
            browser.close()
        print(f"[TikTok Setup] Session saved to {self.cookies_path}. You're set!")
        return True

    def upload_video(self, file_path: str, title: str, tags: list[str]) -> dict:
        """
        Uploads a video to TikTok.
        title  — caption text (TikTok uses caption, not a separate title field)
        tags   — list of hashtag strings WITHOUT the # sign
        """
        if not os.path.exists(file_path):
            return {"status": "Error", "message": f"Video file not found: {file_path}"}

        client = self._get_client()
        if not client:
            return {"status": "Skipped", "message": "TikTok session not configured."}

        # Build caption: title + hashtags
        hashtags = " ".join(f"#{t.strip('#').replace(' ', '')}" for t in tags)
        caption = f"{title}\n\n{hashtags}"[:2200]  # type: ignore

        try:
            print(f"[TikTok] Uploading: {file_path}")
            client.post_video(file_path, caption, self.cookies_path)
            print("[TikTok] Upload successful!")
            return {"status": "Success", "caption": caption}
        except Exception as e:
            print(f"[TikTok] Upload failed: {e}")
            return {"status": "Error", "message": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Uploader")
    parser.add_argument("--setup", action="store_true", help="Run one-time browser login to save TikTok session")
    args = parser.parse_args()

    uploader = TikTokUploader()
    if args.setup:
        uploader.setup_session()
    else:
        print("Usage: python tiktok_uploader.py --setup")

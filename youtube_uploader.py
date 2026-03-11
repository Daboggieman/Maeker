"""
youtube_uploader.py — Full YouTube Data API v3 OAuth2 uploader.

One-time setup
--------------
1. Go to console.cloud.google.com → New Project → Enable "YouTube Data API v3"
2. Credentials → Create OAuth 2.0 Client ID (Desktop app) → Download as client_secrets.json
3. Place client_secrets.json in the maker/ root folder (or set YOUTUBE_CREDENTIALS_PATH in .env)
4. Run the first job with --upload — a browser will open for consent. Token auto-saved after that.

All subsequent uploads use the saved youtube_token.json — no browser needed.
"""
import os
import pickle
from dotenv import load_dotenv  # type: ignore

load_dotenv()

SECRETS_PATH  = os.getenv("YOUTUBE_CREDENTIALS_PATH", "client_secrets.json")
TOKEN_PATH    = os.getenv("YOUTUBE_TOKEN_PATH", "youtube_token.json")
SCOPES        = ["https://www.googleapis.com/auth/youtube.upload"]

# YouTube category IDs (common ones)
CATEGORY_MAP = {
    "History":    "27",   # Education
    "Bible":      "27",
    "Science":    "27",
    "Technology": "28",   # Science & Technology
    "Politics":   "25",   # News & Politics
    "Crime":      "25",
    "Business":   "25",
    "Culture":    "27",
    "Society":    "27",
    "Biography":  "27",
    "General":    "27",
}


class YouTubeUploader:
    def __init__(self, credentials_path=None, token_path=None):
        self.credentials_path = credentials_path or SECRETS_PATH
        self.token_path       = token_path or TOKEN_PATH
        self.youtube          = None

    def authenticate(self) -> bool:
        """Runs OAuth2 flow (browser first time) or loads saved token."""
        try:
            from google.oauth2.credentials import Credentials  # type: ignore
            from google.auth.transport.requests import Request  # type: ignore
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            print(
                "[YouTube] ERROR: Google API libraries not installed.\n"
                "  Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
            )
            return False

        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)

        # Refresh or start new flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print(
                        f"[YouTube] ERROR: client_secrets.json not found at '{self.credentials_path}'.\n"
                        "  Download it from console.cloud.google.com → Credentials → OAuth 2.0 Client IDs."
                    )
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future runs
            with open(self.token_path, "wb") as f:
                pickle.dump(creds, f)

        self.youtube = build("youtube", "v3", credentials=creds)
        print("[YouTube] Authenticated successfully.")
        return True

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category: str = "General",
        privacy: str = "public",
    ) -> dict:
        """Upload a video file. Returns dict with status and video_id on success."""
        if not os.path.exists(file_path):
            return {"status": "Error", "message": f"File not found: {file_path}"}

        if not self.authenticate():
            return {"status": "Error", "message": "YouTube authentication failed."}

        # Satisfy type checkers
        youtube_client = self.youtube
        assert youtube_client is not None

        from googleapiclient.http import MediaFileUpload  # type: ignore

        category_id = CATEGORY_MAP.get(category, "27")
        safe_title = (title or "")[:100]  # type: ignore
        
        body = {
            "snippet": {
                "title": safe_title,
                "description": description or "",
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)

        try:
            print(f"[YouTube] Starting upload: {safe_title}")
            request = youtube_client.videos().insert(part="snippet,status", body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    print(f"[YouTube] Uploading... {pct}%", end="\r")

            assert response is not None
            video_id = response.get("id", "")
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"\n[YouTube] Upload complete! {url}")
            return {"status": "Success", "video_id": video_id, "url": url}

        except Exception as e:
            print(f"\n[YouTube] Upload failed: {e}")
            return {"status": "Error", "message": str(e)}


if __name__ == "__main__":
    uploader = YouTubeUploader()
    uploader.authenticate()

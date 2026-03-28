import os
import asyncio
import re
import edge_tts  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

class VoiceEngine:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_api_key_2 = os.getenv("ELEVENLABS_API_KEY_2")
        self.voice_name = "George"
        self.cached_voice_id = None
        self.edge_fallback_voice = "en-US-ChristopherNeural"

    def _sanitize_text(self, text):
        """Removes markdown, brackets, and meta-text so the AI doesn't speak it."""
        text = re.sub(r'[*_]', '', text)
        text = re.sub(r'[\(\[].*?[\)\]]', '', text)
        text = re.sub(r'^(Scene \d+:|Narration:|Voiceover:|Audio:)\s*', '', text, flags=re.IGNORECASE|re.MULTILINE)
        return text.strip()

    def _get_elevenlabs_voice_id(self, api_key=None):
        """Fetches the specific Voice ID for the requested named voice."""
        if self.cached_voice_id:
            return self.cached_voice_id

        import requests  # type: ignore
        key_to_use = api_key or self.elevenlabs_api_key
        headers = {"xi-api-key": key_to_use}
        try:
            response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
            if response.status_code == 200:
                voices = response.json().get("voices", [])
                for v in voices:
                    api_name = v.get("name", "")
                    # Match on prefix: "Roger" matches "Roger - Laid-Back, Casual, Resonant"
                    if api_name.lower() == self.voice_name.lower() or \
                       api_name.lower().startswith(self.voice_name.lower() + " -"):
                        self.cached_voice_id = v.get("voice_id")
                        return self.cached_voice_id
            print(f"WARN: Could not find ElevenLabs voice '{self.voice_name}'. Using default.")
        except Exception as e:
            print(f"WARN: Failed to search ElevenLabs voices: {e}")

        # Fallback to a well-known default voice if search fails
        self.cached_voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam (Default)
        return self.cached_voice_id

    async def generate_voice(self, text, output_path, provider="edge", tone=None, voice=None):
        """Generates voice. Primary: ElevenLabs, Secondary: Edge TTS"""
        clean_text = self._sanitize_text(text)
        if not clean_text:
            clean_text = "Blank scene."

        keys_to_try = [k for k in [self.elevenlabs_api_key, self.elevenlabs_api_key_2] if k]

        if keys_to_try:
            import requests  # type: ignore
            
            for attempt_idx, current_key in enumerate(keys_to_try):
                # Polite delay to prevent rate limits from consecutive script scenes
                await asyncio.sleep(1.5)
                
                voice_id = self._get_elevenlabs_voice_id(api_key=current_key)
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": current_key
                }
                data = {
                    "text": clean_text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
                }
                try:
                    response = requests.post(url, json=data, headers=headers, timeout=60)
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        return output_path
                    else:
                        # --- Detailed error detection ---
                        error_detail = ""
                        try:
                            body = response.json()
                            detail = body.get("detail", {})
                            if isinstance(detail, dict):
                                error_code = detail.get("status", "")
                            else:
                                error_code = str(detail)
                                
                            key_num = attempt_idx + 1
                            if error_code == "quota_exceeded":
                                print(
                                    f"[ElevenLabs Key {key_num}] QUOTA EXCEEDED — falling back to next key or Edge TTS."
                                )
                                continue # Try next key
                            elif response.status_code == 429:
                                print(f"WARN: [ElevenLabs Key {key_num}] Rate Limit (429). Sleeping 25s to cool down before pursuing alternatives...")
                                await asyncio.sleep(25)
                                continue
                            else:
                                error_detail = f" | error_code={error_code}" if error_code else f" | body={body}"
                                print(f"WARN: ElevenLabs failed with HTTP {response.status_code}{error_detail}. Falling back...")
                        except Exception:
                            print(f"WARN: ElevenLabs failed with HTTP {response.status_code} (non-JSON body).")
                except Exception as e:
                    print(f"WARN: ElevenLabs connection failed: {e}. Falling back...")

        # Fallback: Edge TTS
        print("INFO: Generating voice with Edge TTS fallback.")
        return await self.generate_voice_edge(clean_text, output_path, self.edge_fallback_voice)

    async def generate_voice_edge(self, text, output_path, voice="en-US-ChristopherNeural"):
        """Generates voice using free Microsoft Edge TTS."""
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path

if __name__ == "__main__":
    engine = VoiceEngine()
    # To run: asyncio.run(engine.generate_voice("This is a test script.", "output.mp3", tone="dramatic"))

import os
import asyncio
import edge_tts
from dotenv import load_dotenv

load_dotenv()

class VoiceEngine:
    def __init__(self):
        pass

    async def generate_voice(self, text, output_path, provider="edge", voice=None):
        """Generates voice using free Microsoft Edge TTS."""
        # Force default to Edge TTS regardless of provider arg
        default_voice = voice or "en-US-AndrewNeural"
        return await self.generate_voice_edge(text, output_path, default_voice)

    async def generate_voice_edge(self, text, output_path, voice="en-US-AndrewNeural"):
        """Generates voice using free Microsoft Edge TTS."""
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path

if __name__ == "__main__":
    engine = VoiceEngine()
    # To run: asyncio.run(engine.generate_voice("This is a test script.", "output.mp3"))

import os
import ffmpeg
import requests
import random
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

class VideoCreator:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getenv("BASE_DIR", "c:\\Users\\RAPH-EXT\\maker")
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.renders_dir = os.path.join(self.base_dir, "assets", "renders")
        self.images_dir = os.path.join(self.base_dir, "assets", "images")
        
        # Ensure image dir exists
        os.makedirs(self.images_dir, exist_ok=True)

    def generate_image(self, prompt, output_name):
        """Generates an image using Pollinations.ai (FREE)."""
        try:
            # Seed and dimensions for Pollinations
            seed = random.randint(0, 999999)
            encoded_prompt = quote(prompt)
            # Using FLUX model via Pollinations for high quality
            url = f"https://pollinations.ai/p/{encoded_prompt}?width=1920&height=1080&seed={seed}&model=flux&nologo=true"
            
            output_path = os.path.join(self.images_dir, f"{output_name}.jpg")
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return output_path
            else:
                print(f"WARN: Free image gen failed with status {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Free image generation system failed: {e}")
            return None

    def assemble_video(self, audio_path, image_path, output_name, format="16:9"):
        """Assembles a simple video from an audio file and a static image."""
        
        output_path = os.path.join(self.renders_dir, f"{output_name}.mp4")
        
        # Set resolution based on format
        if format == "9:16":
            width, height = 1080, 1920
        else: # 16:9
            width, height = 1920, 1080

        try:
            input_audio = ffmpeg.input(audio_path)
            duration = float(ffmpeg.probe(audio_path)['format']['duration'])
            
            if image_path:
                input_image = ffmpeg.input(image_path, loop=1, t=duration)
            else:
                # Use black background if no image
                print("INFO: No image provided. Using black background.")
                input_image = ffmpeg.input(f'color=c=black:s={width}x{height}:d={duration}', f='lavfi')

            # Create video stream with scaling and padding
            video = (
                input_image
                .filter('scale', w=width, h=height, force_original_aspect_ratio='decrease')
                .filter('pad', w=width, h=height, x='(ow-iw)/2', y='(oh-ih)/2', color='black')
            )

            (
                ffmpeg
                .output(video, input_audio, output_path, vcodec='libx264', acodec='aac', shortest=None)
                .overwrite_output()
                .run()
            )
            return output_path
        except Exception as e:
            print(f"ERROR assembling video: {e}")
            return None

if __name__ == "__main__":
    creator = VideoCreator()
    creator.assemble_video("audio.mp3", "image.jpg", "test_video")

import os
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

    def generate_image(self, prompt, output_name, topic_folder=None):
        """Generates an image using the premium gen.pollinations.ai API with model failover."""
        import time
        api_key = os.getenv("POLLINATIONS_API_KEY")
        max_retries = 3
        
        models = ["flux", "zimage", "imagen-4"]
        
        for attempt in range(max_retries):
            # Alternate model if first one fails
            model = models[attempt % len(models)]
            
            try:
                seed = random.randint(0, 2147483647)
                encoded_prompt = quote(prompt)
                # Determine output path with topic subfolder support
                folder_path = self.images_dir
                if topic_folder:
                    folder_path = os.path.join(self.images_dir, topic_folder)
                    os.makedirs(folder_path, exist_ok=True)
                
                output_path = os.path.join(folder_path, f"{output_name}.jpg")
                
                # intentional Polite delay
                time.sleep(3.5)
                
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                url = (
                    f"https://gen.pollinations.ai/image/{encoded_prompt}"
                    f"?model={model}&seed={seed}&width=1280&height=720&nologo=true"
                )
                
                response = requests.get(url, headers=headers, timeout=45)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' not in content_type:
                        print(f"WARN: API returned non-image content ({content_type}). Retrying with fallback model...")
                        time.sleep(3)
                        continue
                        
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                elif response.status_code in [530, 429]:
                    print(f"WARN: API Rate Limit/Error {response.status_code}. Backing off... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"WARN: Image gen failed with status {response.status_code}. Retrying...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"ERROR: Image generation request failed: {e}")
                time.sleep(2)
                
        print(f"ERROR: Image generation completely failed after {max_retries} attempts.")
        return None

    def _create_subtitle_clip(self, text, width, duration):
        """Creates a subtitle ImageClip using PIL to completely avoid MoviePy's ImageMagick requirement."""
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        from moviepy import ImageClip
        import textwrap

        img_width = int(width) - 200
        # Estimate height based on wrap
        wrapped_text = "\n".join(textwrap.wrap(text, width=65))
        line_count = len(wrapped_text.split('\n'))
        img_height = max(100, line_count * 50 + 40)

        # Create transparent background
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw semi-transparent background box
        draw.rectangle(((0, 0), (img_width, img_height)), fill=(0, 0, 0, 153))

        # Try to load Arial, fallback to default if not found
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()

        # Draw text centered exactly in the box
        draw.text((img_width/2, img_height/2), wrapped_text, font=font, fill=(255, 255, 255, 255), anchor="mm", align="center")

        # Convert PIL Image to numpy array, then to MoviePy ImageClip
        img_array = np.array(img)
        clip = ImageClip(img_array).with_duration(duration)
        return clip

    def assemble_multi_scene_video(self, scene_assets, output_name, format="16:9"):
        """
        Assembles a multi-scene video using MoviePy v2.
        scene_assets is a list of dicts: [{"audio": "...", "image": "...", "narration": "..."}]
        """
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip
        import traceback
        
        output_path = os.path.join(self.renders_dir, f"{output_name}.mp4")
        
        # Set resolution based on format
        if format == "9:16":
            width, height = 1080, 1920
        else: # 16:9
            width, height = 1920, 1080

        try:
            print(f"INFO: Assembling multi-scene video '{output_name}' with {len(scene_assets)} scenes...")
            clips = []
            
            for index, asset in enumerate(scene_assets):
                audio_path = asset.get("audio")
                image_path = asset.get("image")
                narration = asset.get("narration", "")
                
                if not audio_path or not os.path.exists(audio_path):
                    print(f"WARN: Skipping scene {index+1} due to missing audio.")
                    continue
                    
                # Load Audio to get exact duration
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                
                # Load Image
                if image_path and os.path.exists(image_path):
                    image_clip = ImageClip(image_path).with_duration(duration)
                    if format == "9:16":
                        image_clip = image_clip.resized(height=height).cropped(x_center=image_clip.w/2, width=width)
                else:
                    print(f"WARN: Missing image for scene {index+1}, using black screen.")
                    image_clip = ColorClip(size=(width, height), color=(0,0,0), duration=duration)

                image_clip = image_clip.with_audio(audio_clip)

                # Attempt Subtitles (Custom PIL Implementation)
                try:
                    txt_clip = self._create_subtitle_clip(narration, width, duration)
                    txt_clip = txt_clip.with_position(('center', 'bottom')).margin(bottom=50, opacity=0)
                    scene_clip = CompositeVideoClip([image_clip, txt_clip])
                except Exception as text_e:
                    if index == 0:
                        print(f"WARN: Subtitles skipped due to error: {text_e}")
                    scene_clip = image_clip
                
                clips.append(scene_clip)
            
            if not clips:
                print("ERROR: No valid scenes generated.")
                return None
                
            # Combine all scenes back-to-back perfectly
            final_video = concatenate_videoclips(clips, method="compose")
            
            print(f"INFO: Writing video file to {output_path} (this will take a while)...")
            final_video.write_videofile(
                output_path, 
                fps=24, 
                codec='libx264', 
                audio_codec='aac',
                logger=None # Suppress massive progress bars in terminal to prevent maxBuffer error
            )
            
            # Close resources to prevent file locking/memory leaks
            for clip in clips:
                clip.close()
            final_video.close()
            
            return output_path
        except Exception as e:
            print(f"ERROR assembling multi-scene video: {e}")
            traceback.print_exc()
            return None

if __name__ == "__main__":
    creator = VideoCreator()
    mock_assets = [{"audio": "audio.mp3", "image": "image.jpg", "narration": "Test scene."}]
    creator.assemble_multi_scene_video(mock_assets, "test_video")

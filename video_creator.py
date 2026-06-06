import os
import requests  # type: ignore
import random
from urllib.parse import quote
from dotenv import load_dotenv  # type: ignore

load_dotenv()

class VideoCreator:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getenv("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.renders_dir = os.path.join(self.base_dir, "assets", "renders")
        self.images_dir = os.path.join(self.base_dir, "assets", "images")
        
        # Ensure image dir exists
        os.makedirs(self.images_dir, exist_ok=True)

    def generate_image(self, prompt, output_name, topic_folder=None):
        """Generates an image using the premium gen.pollinations.ai API with model failover."""
        import time
        api_key = os.getenv("POLLINATIONS_API_KEY")
        max_retries = 5

        models = ["flux", "zimage", "imagen-4"]

        # --- Cache: skip generation if file already exists ---
        folder_path = self.images_dir
        if topic_folder:
            folder_path = os.path.join(self.images_dir, topic_folder)
        output_path = os.path.join(folder_path, f"{output_name}.jpg")
        if os.path.exists(output_path):
            print(f"[cache] Image already exists, skipping generation: {output_path}")
            return output_path

        for attempt in range(max_retries):
            # Alternate model if first one fails
            model = models[attempt % len(models)]

            try:
                seed = random.randint(0, 2147483647)
                encoded_prompt = quote(prompt)
                # Determine output path with topic subfolder support
                os.makedirs(folder_path, exist_ok=True)

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
                        print(f"WARN: Image API returned non-image content ({content_type}). Retrying with alternate model...")
                        time.sleep(3)
                        continue

                    # Determine output path with topic subfolder support
                    os.makedirs(folder_path, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path

                elif response.status_code == 530:
                    print(f"WARN: Model {model} potentially rejected the prompt (NSFW/530). Fast switching to next model...")
                    time.sleep(2)
                elif response.status_code in [424, 429, 500, 502, 503]:
                    wait_time = 12 * (attempt + 1)
                    print(f"WARN: [IMAGE API {response.status_code}] Service unavailable or Rate Limit. Backing off {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"WARN: Image gen failed with HTTP {response.status_code}. Retrying...")
                    time.sleep(3)

            except Exception as e:
                print(f"ERROR: Image generation request failed: {e}")
                time.sleep(2)

        print(f"ERROR: Image generation completely failed after {max_retries} attempts.")
        return None

    def fetch_background_music(self, theme: str, job_id: str) -> str | None:
        """
        Downloads a royalty-free background music track relevant to the video theme.
        Tries Pixabay API first, falls back to a hardcoded public-domain ambient URL.
        Saves to assets/music/{job_id}_bg.mp3.
        """
        music_dir = os.path.join(self.assets_dir, "music")
        os.makedirs(music_dir, exist_ok=True)
        out_path = os.path.join(music_dir, f"{job_id}_bg.mp3")

        if os.path.exists(out_path):
            print(f"[cache] Background music already exists: {out_path}")
            return out_path

        pixabay_key = os.getenv("PIXABAY_API_KEY", "")
        if pixabay_key:
            try:
                # Search for a track matching the theme
                q = quote(theme[:30])  # type: ignore
                resp = requests.get(
                    f"https://pixabay.com/api/?key={pixabay_key}&q={q}&media_type=music&per_page=3",
                    timeout=15
                )
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    if hits:
                        audio_url = hits[0].get("audio", "")
                        if audio_url:
                            dl = requests.get(audio_url, timeout=60)
                            if dl.status_code == 200:
                                with open(out_path, "wb") as f:
                                    f.write(dl.content)
                                print(f"[music] Downloaded from Pixabay: {out_path}")
                                return out_path
            except Exception as e:
                print(f"WARN: Pixabay music fetch failed: {e}. Trying fallback...")

        # Fallback: a known public-domain ambient track from Free Music Archive
        FALLBACK_URL = (
            "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/"
            "no_curator/Tours/Enthusiast/Tours_-_01_-_Enthusiast.mp3"
        )
        try:
            dl = requests.get(FALLBACK_URL, timeout=60)
            if dl.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(dl.content)
                print(f"[music] Downloaded fallback ambient track: {out_path}")
                return out_path
        except Exception as e:
            print(f"WARN: Fallback music download also failed: {e}")

        return None


    def _create_subtitle_clips(self, text, width, duration, height):
        """
        Creates a list of subtitle ImageClips that show one line at a time
        across the duration of the scene instead of a static paragraph.
        """
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        import numpy as np  # type: ignore
        from moviepy import ImageClip  # type: ignore

        # Try to load Arial Bold, fallback to Arial, then default
        try:
            font = ImageFont.truetype("arialbd.ttf", 85)
        except IOError:
            try:
                font = ImageFont.truetype("arial.ttf", 85)
            except IOError:
                font = ImageFont.load_default()

        # Split text into bite-sized lines (roughly 1-2 words per line)
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(current_line) >= 2 or len(" ".join(current_line)) > 14:
                lines.append(" ".join(current_line))
                current_line = []
        if current_line:
            lines.append(" ".join(current_line))

        if not lines:
            return []

        # Calculate duration per line
        time_per_line = duration / len(lines)
        subtitle_clips = []
        current_start_time = 0.0

        for line in lines:
            # Estimate text bounding box to draw the background correctly
            # Create a dummy image to use ImageDraw.textbbox
            dummy_img = Image.new('RGBA', (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_img)
            bbox = dummy_draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Paddings for background box
            box_width = text_width + 80
            box_height = text_height + 50

            # Expand image size slightly to accommodate drop shadows and rounded corners nicely
            img_w = box_width + 20
            img_h = box_height + 20
            img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            box_x = 10
            box_y = 10

            # Subtle drop shadow for the box itself
            draw.rounded_rectangle(((box_x + 6, box_y + 6), (box_x + box_width + 6, box_y + box_height + 6)), radius=15, fill=(0, 0, 0, 100))
            
            # Draw premium smooth rounded background box
            draw.rounded_rectangle(((box_x, box_y), (box_x + box_width, box_y + box_height)), radius=15, fill=(0, 0, 0, 200))

            # Draw text text drop-shadow
            draw.text((box_x + box_width/2 + 4, box_y + box_height/2 + 4), line, font=font, fill=(0,0,0,220), anchor="mm", align="center")
            
            # Draw text centered in the box (Pure Yellow + Black Stroke)
            draw.text((box_x + box_width/2, box_y + box_height/2), line, font=font, fill="#FFD700", anchor="mm", align="center", stroke_width=3, stroke_fill="black")

            # Convert to MoviePy ImageClip
            img_array = np.array(img)
            clip = ImageClip(img_array).with_duration(time_per_line)
            
            # Position the clip at the direct center of the screen
            clip = clip.with_start(current_start_time).with_position(('center', 'center')) # type: ignore
            
            subtitle_clips.append(clip)
            current_start_time += time_per_line

        return subtitle_clips

    def _get_scene_watermark(self, width, duration):
        """Generates a semi-transparent keyboard-key sized watermark clip."""
        from PIL import Image, ImageDraw, ImageFont # type: ignore
        import numpy as np # type: ignore
        from moviepy import ImageClip # type: ignore
        
        try:
            logo_path = os.path.join("media", "maeker logo.png")
            if not os.path.exists(logo_path):
                return None
                
            wm_logo = Image.open(logo_path).convert("RGBA")
            
            # Make keyboard-key sized (~45px height)
            target_h = 45
            hpercent = (target_h / float(wm_logo.size[1]))
            wsize = int((float(wm_logo.size[0]) * float(hpercent)))
            wm_logo = wm_logo.resize((wsize, target_h), Image.Resampling.LANCZOS)
            
            # Create font
            try:
                font = ImageFont.truetype("arialbd.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            # Measure text
            text = "MAEKER"
            dummy_img = Image.new('RGBA', (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_img)
            bbox = dummy_draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            
            spacing = 12
            wm_width = wsize + spacing + tw
            wm_height = max(target_h, th)
            
            wm_img = Image.new("RGBA", (wm_width, wm_height), (0, 0, 0, 0))
            wm_img.paste(wm_logo, (0, (wm_height - target_h) // 2), wm_logo)
            
            wm_draw = ImageDraw.Draw(wm_img)
            wm_draw.text((wsize + spacing, (wm_height - th) // 2 - 5), text, font=font, fill=(255, 255, 255, 255))
            
            # 80% opacity as requested
            r, g, b, a = wm_img.split()
            a = a.point(lambda p: int(p * 0.8))
            wm_img.putalpha(a)
            
            wm_array = np.array(wm_img)
            wm_clip = ImageClip(wm_array).with_duration(duration)
            
            # Position top right with 40px padding
            return wm_clip.with_position((width - wm_width - 40, 40)) # type: ignore
        except Exception as e:
            print(f"WARN: Watermark generation failed: {e}")
            return None

    def create_scene_clip(self, asset, output_path, format="16:9"):
        """
        Renders a single scene asset to a standalone MP4 file for caching.
        """
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, ColorClip # type: ignore
        import numpy as np # type: ignore
        
        audio_path = asset.get("audio")
        image_path = asset.get("image")
        narration = asset.get("narration", "")
        
        if not audio_path or not os.path.exists(audio_path):
            return False
            
        # Set resolution
        if format == "9:16":
            width, height = 720, 1280
        else: # 16:9
            width, height = 1280, 720
            
        try:
            # Load Audio
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # Load Image
            if image_path and os.path.exists(image_path):
                image_clip = ImageClip(image_path).with_duration(duration)
                if image_clip.size != (width, height):
                    # Resize to fill, then crop to target bounds
                    img_ratio = image_clip.w / image_clip.h  # type: ignore
                    target_ratio = width / height
                    if img_ratio > target_ratio:
                        image_clip = image_clip.resized(height=height)
                        image_clip = image_clip.cropped(x_center=image_clip.w/2, width=width, y_center=image_clip.h/2, height=height)
                    else:
                        image_clip = image_clip.resized(width=width)
                        image_clip = image_clip.cropped(x_center=image_clip.w/2, width=width, y_center=image_clip.h/2, height=height)
            else:
                image_clip = ColorClip(size=(width, height), color=(0,0,0), duration=duration)
                
            image_clip = image_clip.with_audio(audio_clip)
            
            # Subtitles
            sub_clips = self._create_subtitle_clips(narration, width, duration, height)
            
            # Watermark
            wm_clip = self._get_scene_watermark(width, duration)
            
            layers = [image_clip]
            if sub_clips:
                layers.extend(sub_clips)
            if wm_clip:
                layers.append(wm_clip)
                
            final_scene = CompositeVideoClip(layers)
            
            # Write to disk
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            final_scene.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                logger=None,
                threads=1,
                preset='ultrafast'
            )
            
            final_scene.close()
            audio_clip.close()
            if image_clip:
                try: image_clip.close()
                except: pass
            if wm_clip:
                try: wm_clip.close()
                except: pass
            if sub_clips:
                for sc in sub_clips:
                    try: sc.close()
                    except: pass
            return True
            
        except Exception as e:
            print(f"ERROR rendering scene clip: {e}")
            return False

    def assemble_multi_scene_video(self, scene_assets, output_name, format="16:9", music_path=None):
        """
        Assembles a multi-scene video using ffmpeg for ultra-low memory usage.
        scene_assets is a list of dicts: [{"audio": "...", "image": "...", "narration": "..."}]
        """
        import subprocess
        import traceback
        output_path = os.path.join(self.renders_dir, f"{output_name}.mp4")

        try:
            print(f"INFO: Assembling multi-scene video '{output_name}' with {len(scene_assets)} scenes via ffmpeg...")
            
            # Ensure all scenes have their video_cache ready
            for i, asset in enumerate(scene_assets):
                if not asset.get("video_cache") or not os.path.exists(asset.get("video_cache")):
                    print(f"WARN: Scene {i+1} is missing its video_cache. Attempting to render it...")
                    temp_cache = os.path.join(self.renders_dir, f"temp_cache_{output_name}_{i}.mp4")
                    if self.create_scene_clip(asset, temp_cache, format):
                        asset["video_cache"] = temp_cache
                    else:
                        print(f"ERROR: Could not render missing cache for scene {i+1}.")
                        return None
            
            # Create concat list file
            concat_file_path = os.path.join(self.renders_dir, f"concat_{output_name}.txt")
            with open(concat_file_path, "w", encoding="utf-8") as f:
                for asset in scene_assets:
                    # ffmpeg requires forward slashes or escaped backslashes
                    safe_path = asset['video_cache'].replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")

            if music_path and os.path.exists(music_path):
                temp_combined = os.path.join(self.renders_dir, f"temp_{output_name}.mp4")
                
                # Step 1: Concat with re-encoding for consistent stream compatibility
                r1 = subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file_path,
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    temp_combined
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if r1.returncode != 0:
                    print(f"ERROR: ffmpeg concat failed:\n{r1.stderr.decode(errors='replace')}")
                    return None
                
                # Step 2: Mix background music (looping music stream, amix)
                print(f"INFO: Mixing background music into '{output_path}'...")
                music_safe = music_path.replace("\\", "/")
                r2 = subprocess.run([
                    "ffmpeg", "-y", "-i", temp_combined,
                    "-stream_loop", "-1", "-i", music_safe,
                    "-filter_complex", "[1:a]volume=0.12[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[outa]",
                    "-map", "0:v", "-map", "[outa]",
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "192k",
                    output_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                
                if os.path.exists(temp_combined):
                    os.remove(temp_combined)
                    
                if r2.returncode != 0:
                    print(f"ERROR: ffmpeg music mix failed:\n{r2.stderr.decode(errors='replace')}")
                    return None
            else:
                # Direct concat with re-encoding for consistent stream compatibility
                r = subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file_path,
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    output_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if r.returncode != 0:
                    print(f"ERROR: ffmpeg concat failed:\n{r.stderr.decode(errors='replace')}")
                    return None

            if os.path.exists(concat_file_path):
                os.remove(concat_file_path)
                
            print(f"INFO: Successfully assembled final video: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"ERROR assembling multi-scene video: {e}")
            traceback.print_exc()
            return None

    def append_outro(self, main_video_path: str, outro_path: str) -> str:
        """
        Concatenates the branded outro clip to the end of the main video.
        Returns path to the final video as {name}_final.mp4.
        """
        if not outro_path or not os.path.exists(outro_path):
            print("[outro] No outro found — skipping append.")
            return main_video_path

        try:
            from moviepy import VideoFileClip, concatenate_videoclips  # type: ignore

            print("[outro] Appending Maeker Studios outro...")
            main_clip  = VideoFileClip(main_video_path)
            outro_clip = VideoFileClip(outro_path)

            # Ensure same size — resize outro to match main if needed
            if outro_clip.size != main_clip.size:
                outro_clip = outro_clip.resized(main_clip.size)

            final = concatenate_videoclips([main_clip, outro_clip], method="compose")

            final_path = main_video_path.replace(".mp4", "_final.mp4")
            final.write_videofile(
                final_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None,
                threads=1,
                preset='ultrafast'
            )

            main_clip.close()
            outro_clip.close()
            final.close()

            print(f"[outro] Final video with outro: {final_path}")
            return final_path

        except Exception as e:
            print(f"WARN: Could not append outro: {e}")
            return main_video_path


if __name__ == "__main__":
    creator = VideoCreator()
    mock_assets = [{"audio": "audio.mp3", "image": "image.jpg", "narration": "Test scene."}]
    creator.assemble_multi_scene_video(mock_assets, "test_video")


import os
import requests  # type: ignore
import random
from urllib.parse import quote
from dotenv import load_dotenv  # type: ignore

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
                    time.sleep(10 * (attempt + 1))
                else:
                    print(f"WARN: Image gen failed with status {response.status_code}. Retrying...")
                    time.sleep(2)

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

        # Try to load Arial, fallback to default if not found
        try:
            font = ImageFont.truetype("arial.ttf", 45)
        except IOError:
            font = ImageFont.load_default()

        # Split text into bite-sized lines (roughly 5-7 words per line)
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 35: # Approx char limit per line
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
            box_width = text_width + 60
            box_height = text_height + 40

            # Create transparent background for this specific subtitle slice
            img = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Draw semi-transparent background box
            draw.rectangle(((0, 0), (box_width, box_height)), fill=(0, 0, 0, 50))

            # Draw text centered in the box
            draw.text((box_width/2, box_height/2), line, font=font, fill=(255, 255, 255, 255), anchor="mm", align="center")

            # Convert to MoviePy ImageClip
            img_array = np.array(img)
            clip = ImageClip(img_array).with_duration(time_per_line)
            
            # Position the clip at the bottom of the screen
            clip = clip.with_start(current_start_time).with_position(('center', height - box_height - 90)) # type: ignore
            
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
                logger=None
            )
            
            final_scene.close()
            audio_clip.close()
            return True
            
        except Exception as e:
            print(f"ERROR rendering scene clip: {e}")
            return False

    def assemble_multi_scene_video(self, scene_assets, output_name, format="16:9", music_path=None):
        """
        Assembles a multi-scene video using MoviePy v2.
        scene_assets is a list of dicts: [{"audio": "...", "image": "...", "narration": "..."}]
        music_path: optional path to a background music file (will be mixed at 12% volume).
        """
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip, vfx  # type: ignore
        import traceback
        
        output_path = os.path.join(self.renders_dir, f"{output_name}.mp4")
        
        # Set resolution based on format
        if format == "9:16":
            width, height = 720, 1280
        else: # 16:9
            width, height = 1280, 720

        try:
            print(f"INFO: Assembling multi-scene video '{output_name}' with {len(scene_assets)} scenes...")
            clips = []
            
            for index, asset in enumerate(scene_assets):
                # Prefer pre-rendered cache (Plan 1)
                cache_path = asset.get("video_cache")
                if cache_path and os.path.exists(cache_path):
                    from moviepy import VideoFileClip # type: ignore
                    clips.append(VideoFileClip(cache_path))
                    continue

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
                # Load Image and force strictly to exact (width, height)
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
                    print(f"WARN: Missing image for scene {index+1}, using black screen.")
                    image_clip = ColorClip(size=(width, height), color=(0,0,0), duration=duration)

                image_clip = image_clip.with_audio(audio_clip)

                # Subtitles & Watermark
                sub_clips = self._create_subtitle_clips(narration, width, duration, height)
                wm_clip = self._get_scene_watermark(width, duration)
                
                layers = [image_clip]
                if sub_clips:
                    layers.extend(sub_clips)
                if wm_clip:
                    layers.append(wm_clip)
                
                clips.append(CompositeVideoClip(layers))
            
            if not clips:
                print("ERROR: No valid scenes generated.")
                return None

            # ==== BATCH CHUNKING LOGIC ====
            chunk_size = 5
            chunk_files = []
            
            for i in range(0, len(clips), chunk_size):
                chunk_clips = clips[i:i + chunk_size]  # type: ignore
                chunk_path = os.path.join(self.renders_dir, f"temp_{output_name}_chunk_{i//chunk_size}.mp4")
                
                print(f"INFO: Rendering chunk {i//chunk_size + 1}/{(len(clips) + chunk_size - 1)//chunk_size}...")
                
                # Apply crossfades WITHIN the chunk
                trans_clips = [chunk_clips[0]]
                for c in chunk_clips[1:]:  # type: ignore
                    trans_clips.append(c.with_effects([vfx.CrossFadeIn(1.0)]))

                chunk_video = concatenate_videoclips(trans_clips, method="compose", padding=-1.0)
                chunk_video.write_videofile(
                    chunk_path,
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    logger=None
                )
                
                # Close memory
                chunk_video.close()
                for c in chunk_clips:
                    c.close()

                chunk_files.append(chunk_path)

            print(f"INFO: Combining {len(chunk_files)} rendered chunks together...")
            
            # Combine the physical chunk files together (No compose padding across chunks to save RAM)
            from moviepy import VideoFileClip, CompositeVideoClip  # type: ignore
            loaded_chunks = [VideoFileClip(cf) for cf in chunk_files]
            final_video = concatenate_videoclips(loaded_chunks, method="compose")

            # --- Persistent Watermark ---
            try:
                from PIL import Image, ImageDraw, ImageFont # type: ignore
                import numpy as np # type: ignore
                from moviepy import ImageClip # type: ignore
                
                logo_path = os.path.join("media", "maeker logo.png")
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
                
                # Create combined watermark image
                spacing = 12
                wm_width = wsize + spacing + tw
                wm_height = max(target_h, th)
                
                wm_img = Image.new("RGBA", (wm_width, wm_height), (0, 0, 0, 0))
                wm_img.paste(wm_logo, (0, (wm_height - target_h) // 2), wm_logo)
                
                wm_draw = ImageDraw.Draw(wm_img)
                wm_draw.text((wsize + spacing, (wm_height - th) // 2 - 5), text, font=font, fill=(255, 255, 255, 255))
                
                # Make slightly transparent (60% opacity)
                r, g, b, a = wm_img.split()
                a = a.point(lambda p: int(p * 0.8))
                wm_img.putalpha(a)
                
                wm_array = np.array(wm_img)
                wm_clip = ImageClip(wm_array).with_duration(final_video.duration)
                
                # Position top right with 40px padding
                wm_clip = wm_clip.with_position((width - wm_width - 40, 40)) # type: ignore
                
                final_video = CompositeVideoClip([final_video, wm_clip])
                print("[watermark] Keyboard-key sized transparent watermark applied to top right.")
            except Exception as wm_err:
                print(f"WARN: Could not apply watermark: {wm_err}")

            # --- Optional background music mix ---
            if music_path and os.path.exists(music_path):
                try:
                    from moviepy import AudioFileClip, CompositeAudioClip  # type: ignore
                    bg_audio = AudioFileClip(music_path)
                    total_duration = final_video.duration
                    # Loop music to match video length
                    if bg_audio.duration < total_duration:
                        import math
                        loops = math.ceil(total_duration / bg_audio.duration)
                        from moviepy import concatenate_audioclips  # type: ignore
                        bg_audio = concatenate_audioclips([bg_audio] * loops)
                    bg_audio = bg_audio.subclipped(0, total_duration).with_volume_scaled(0.12)
                    main_audio = final_video.audio
                    if main_audio:
                        mixed = CompositeAudioClip([main_audio, bg_audio])
                        final_video = final_video.with_audio(mixed)
                    print("[music] Background music mixed in at 12% volume.")
                except Exception as music_err:
                    print(f"WARN: Could not mix background music: {music_err}")

            print(f"INFO: Writing final assembled video file to {output_path}...")
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                logger=None 
            )
            
            # Clean up
            final_video.close()
            for lc in loaded_chunks:
                lc.close()
            for cf in chunk_files:
                if os.path.exists(cf):
                    os.remove(cf)
            
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


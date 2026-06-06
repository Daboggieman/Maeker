"""
outro_maker.py — Generates the Maeker Studios branded animated outro clip.
Rendered entirely via MoviePy + PIL. No external video files required.
Output is cached at assets/outro/maeker_outro.mp4.
"""
import os
import math
import numpy as np  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

OUTRO_DURATION = 8.0
FPS = 24
WIDTH, HEIGHT = 1920, 1080

# Brand colours
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
GOLD   = (212, 175, 55)


def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out curve (0→1)."""
    return t * t * (3 - 2 * t)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
        else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except IOError:
            pass
    return ImageFont.load_default()


LOGO_PATH = os.path.join("media", "maeker logo.png")
_logo_img = None
try:
    _logo_img = Image.open(LOGO_PATH).convert("RGBA")
    target_w = 600
    wpercent = (target_w / float(_logo_img.size[0]))
    hsize = int((float(_logo_img.size[1]) * float(wpercent)))
    _logo_img = _logo_img.resize((target_w, hsize), Image.Resampling.LANCZOS)
except Exception as e:
    print(f"WARN: Could not load logo at {LOGO_PATH}: {e}")

def _make_frame(t: float) -> np.ndarray:
    """
    Render a single frame at time t (seconds).

    Timeline
    --------
    0.0 – 1.5s  Logo & 'MAEKER' fade in 
    1.0 – 2.3s  'STUDIOS' fades in  (gold, lighter)
    2.0 – 3.2s  Gold rule draws left → right
    3.0 – 4.5s  CTA (Like/Share) fades in & bounces up
    Hold on final frame until 8.0s
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*BLACK, 255))
    draw = ImageDraw.Draw(img)

    # LOGOs
    fade_maeker = _ease_in_out(min(1.0, t / 1.5))
    if fade_maeker > 0:
        alpha = int(255 * fade_maeker)
        logo_y_bottom = HEIGHT // 2 - 10  # Track where logo ends
        
        # Image Logo
        if _logo_img:
            logo_frame = _logo_img.copy()
            if logo_frame.mode == "RGBA":
                r, g, b, a = logo_frame.split()
                a = a.point(lambda p: int(p * fade_maeker))
                logo_frame.putalpha(a)
            
            lw, lh = logo_frame.size
            logo_x = (WIDTH - lw) // 2
            logo_y = HEIGHT // 2 - lh - 80
            logo_y_bottom = logo_y + lh
            
            img.paste(logo_frame, (logo_x, logo_y), logo_frame)
            
        # "MAEKER" text
        font_m = _load_font(120, bold=True)
        text_m = "MAEKER"
        bbox_m = draw.textbbox((0, 0), text_m, font=font_m)
        tw_m, th_m = bbox_m[2] - bbox_m[0], bbox_m[3] - bbox_m[1]
        
        draw.text(
            ((WIDTH - tw_m) // 2, logo_y_bottom + 10),
            text_m,
            font=font_m,
            fill=(*WHITE, alpha)
        )

    # "STUDIOS"
    fade_studios = _ease_in_out(max(0.0, min(1.0, (t - 1.0) / 1.3)))
    if fade_studios > 0:
        font_s = _load_font(80, bold=False)
        text = "STUDIOS"
        bbox = draw.textbbox((0, 0), text, font=font_s)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # Blend gold with black based on alpha
        r = int(GOLD[0] * fade_studios)
        g = int(GOLD[1] * fade_studios)
        b = int(GOLD[2] * fade_studios)
        draw.text(
            ((WIDTH - tw) // 2, HEIGHT // 2 + 50),
            text,
            font=font_s,
            fill=(r, g, b, 255),
        )

    # Gold rule
    rule_progress = _ease_in_out(max(0.0, min(1.0, (t - 2.0) / 1.2)))
    if rule_progress > 0:
        rule_y = HEIGHT // 2 + 160
        rule_left = WIDTH // 2 - 400
        rule_right = rule_left + int(800 * rule_progress)
        draw.rectangle([rule_left, rule_y, rule_right, rule_y + 3], fill=(*GOLD, 255))

    # Animated CTA (Like, Subscribe, Share)
    # Fades in and slides up between 3.0s and 4.5s
    cta_progress = _ease_in_out(max(0.0, min(1.0, (t - 3.0) / 1.5)))
    if cta_progress > 0:
        font_cta = _load_font(50, bold=True)
        text_cta = "LIKE     SUBSCRIBE     SHARE"
        bbox_cta = draw.textbbox((0, 0), text_cta, font=font_cta)
        tw_cta, th_cta = bbox_cta[2] - bbox_cta[0], bbox_cta[3] - bbox_cta[1]
        
        # Alpha fade
        cta_alpha = int(255 * cta_progress)
        
        # Slide up animation (Y moves from +50 drop to 0)
        y_offset = int(50 * (1.0 - cta_progress))
        cta_y = HEIGHT - 200 + y_offset
        
        draw.text(
            ((WIDTH - tw_cta) // 2, cta_y),
            text_cta,
            font=font_cta,
            fill=(255, 255, 255, cta_alpha),
        )
    return np.array(img.convert("RGB"))


class OutroMaker:
    def __init__(self):
        assets_dir = os.getenv("ASSETS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
        self.outro_path = os.path.join(assets_dir, "outro", "maeker_outro.mp4")

    def build_outro(self) -> str:
        """Render and cache the outro clip. Returns the path to the mp4 file."""
        os.makedirs(os.path.dirname(self.outro_path), exist_ok=True)

        if os.path.exists(self.outro_path):
            print(f"[outro] Using cached outro: {self.outro_path}")
            return self.outro_path

        print("[outro] Rendering Maeker Studios outro clip...")

        try:
            from moviepy import VideoClip, AudioFileClip  # type: ignore
        except ImportError:
            from moviepy.editor import VideoClip  # type: ignore

        clip = VideoClip(_make_frame, duration=OUTRO_DURATION)
        clip = clip.with_fps(FPS)

        clip.write_videofile(
            self.outro_path,
            fps=FPS,
            codec="libx264",
            audio=False,
            logger=None,
        )
        clip.close()
        print(f"[outro] Outro rendered to: {self.outro_path}")
        return self.outro_path


if __name__ == "__main__":
    om = OutroMaker()
    path = om.build_outro()
    print("Done:", path)

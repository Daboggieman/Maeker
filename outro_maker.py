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

OUTRO_DURATION = 4.0   # seconds
FPS = 24
WIDTH, HEIGHT = 1920, 1080
OUTRO_PATH = os.path.join(os.getenv("ASSETS_DIR", "assets"), "outro", "maeker_outro.mp4")

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
    # Pre-scale logo so it's a good size (approx 600px wide)
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
    0.0 – 1.5s  Logo fades in 
    1.0 – 2.3s  "STUDIOS" fades in  (gold, lighter)
    2.0 – 3.2s  Gold rule draws left → right
    3.0 – 4.0s  Hold on final frame
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*BLACK, 255))
    draw = ImageDraw.Draw(img)

    # ── LOGO ──────────────────────────────────────────────────────────
    fade_maeker = _ease_in_out(min(1.0, t / 1.5))
    if fade_maeker > 0 and _logo_img:
        # Create a copy to adjust transparency
        logo_frame = _logo_img.copy()
        alpha = int(255 * fade_maeker)
        
        # Apply the fade to the alpha channel of the logo
        if logo_frame.mode == "RGBA":
            r, g, b, a = logo_frame.split()
            a = a.point(lambda p: int(p * fade_maeker))
            logo_frame.putalpha(a)
        
        # Calculate center position above where "STUDIOS" will be
        lw, lh = logo_frame.size
        logo_x = (WIDTH - lw) // 2
        logo_y = HEIGHT // 2 - lh - 10
        
        # Paste logo using itself as a mask for transparency
        img.paste(logo_frame, (logo_x, logo_y), logo_frame)

    # ── "STUDIOS" ─────────────────────────────────────────────────────────
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
            ((WIDTH - tw) // 2, HEIGHT // 2 + 20),
            text,
            font=font_s,
            fill=(r, g, b, 255),
        )

    # ── Gold rule ─────────────────────────────────────────────────────────
    rule_progress = _ease_in_out(max(0.0, min(1.0, (t - 2.0) / 1.2)))
    if rule_progress > 0:
        rule_y = HEIGHT // 2 + 130
        rule_left = WIDTH // 2 - 400
        rule_right = rule_left + int(800 * rule_progress)
        draw.rectangle([rule_left, rule_y, rule_right, rule_y + 3], fill=(*GOLD, 255))

    # Convert back to RGB array for MoviePy (which expects 3 channels usually)
    return np.array(img.convert("RGB"))


class OutroMaker:
    def __init__(self):
        self.outro_path = OUTRO_PATH

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

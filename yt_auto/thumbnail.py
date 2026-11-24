from PIL import Image, ImageDraw, ImageFont
from config import FONT

def make(text, path, bg=None):
    img = Image.open(bg).convert("RGB").resize((1280, 720)) if bg else Image.new("RGB", (1280, 720), (27, 42, 65))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 150)
    d.rectangle([0, 420, 1280, 720], fill=(0, 0, 0))
    w = d.textlength(text, font=f)
    d.text(((1280 - w) / 2, 480), text, font=f, fill=(255, 220, 0), stroke_width=6, stroke_fill=(0, 0, 0))
    img.save(path)

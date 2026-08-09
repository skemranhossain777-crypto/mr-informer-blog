"""One-off generator for the branded 1200x630 Open Graph / social share image.
Run manually whenever the logo or hero background changes: python generate_social_card.py
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")

W, H = 1200, 630
OUT_PATH = os.path.join(ASSETS, "og-social-card.jpg")

FONT_BOLD = "C:\\Windows\\Fonts\\segoeuib.ttf"
FONT_REG = "C:\\Windows\\Fonts\\segoeui.ttf"


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=255)
    return mask


def build():
    # 1. Background: cover-crop the hero photo to 1200x630, darken it, blur slightly.
    bg = Image.open(os.path.join(ASSETS, "hero_tech_cyber.jpg")).convert("RGB")
    bg = ImageOps.fit(bg, (W, H), method=Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(1.5))

    # Dark gradient overlay (left->right, stronger on the left where text sits)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("L", (W, 1))
    for x in range(W):
        t = x / W
        alpha = int(235 * (1 - t) + 120 * t)
        grad.putpixel((x, 0), alpha)
    grad = grad.resize((W, H))
    black = Image.new("RGBA", (W, H), (10, 12, 20, 255))
    overlay = Image.composite(black, overlay, grad)
    canvas = Image.alpha_composite(bg.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(canvas)

    # 2. Logo badge (rounded square) top-left.
    logo_size = 108
    logo = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGB").resize(
        (logo_size, logo_size), Image.LANCZOS
    )
    mask = rounded_mask((logo_size, logo_size), 26)
    logo_pos = (80, 90)
    canvas.paste(logo, logo_pos, mask)

    # 3. Wordmark next to the logo.
    f_word = ImageFont.truetype(FONT_BOLD, 46)
    draw.text((80 + logo_size + 26, 90 + 18), "MR. INFORMER", font=f_word, fill=(255, 255, 255, 255))
    f_sub = ImageFont.truetype(FONT_REG, 24)
    draw.text((80 + logo_size + 26, 90 + 66), "mr-informer.top", font=f_sub, fill=(120, 210, 255, 255))

    # 4. Headline.
    f_headline = ImageFont.truetype(FONT_BOLD, 58)
    lines = ["Tech, AI & Cybersecurity", "Briefings — Honestly Sourced"]
    y = 300
    for line in lines:
        draw.text((80, y), line, font=f_headline, fill=(255, 255, 255, 255))
        y += 70

    # 5. Tagline.
    f_tag = ImageFont.truetype(FONT_REG, 28)
    draw.text(
        (80, y + 16),
        "Real reporting, clearly summarized, always linked to the source.",
        font=f_tag,
        fill=(200, 210, 225, 255),
    )

    # 6. Category chips (bottom).
    chips = ["AI & Future", "Cyber Security", "Deep Dives", "Tech Pulse"]
    f_chip = ImageFont.truetype(FONT_REG, 22)
    cx = 80
    cy = H - 78
    for chip in chips:
        bbox = draw.textbbox((0, 0), chip, font=f_chip)
        tw = bbox[2] - bbox[0]
        pad_x, pad_y = 20, 10
        chip_w, chip_h = tw + pad_x * 2, 40
        draw.rounded_rectangle(
            [(cx, cy), (cx + chip_w, cy + chip_h)], radius=20, outline=(255, 255, 255, 160), width=1
        )
        draw.text((cx + pad_x, cy + pad_y - 2), chip, font=f_chip, fill=(230, 235, 245, 255))
        cx += chip_w + 16

    final = canvas.convert("RGB")
    final.save(OUT_PATH, "JPEG", quality=90, optimize=True)
    print(f"Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.0f} KB, {final.size})")


if __name__ == "__main__":
    build()

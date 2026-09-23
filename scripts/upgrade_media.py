import os
import sys
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.catalog.models import Category, Product
from apps.combos.models import FixedCombo
from django.core.files import File

BRAIN_DIR = r"C:\Users\DELL\.gemini\antigravity-ide\brain\ae4ca3fe-0c1c-4895-8d5e-092407c5859f"

# High-res source photos
IMG_DAILY = os.path.join(BRAIN_DIR, "category_daily_essentials_1789660714086.jpg")
IMG_ROYAL = os.path.join(BRAIN_DIR, "category_royal_heritage_1789660732786.jpg")
IMG_STREET = os.path.join(BRAIN_DIR, "category_street_food_1789660750837.jpg")
IMG_BRAND = os.path.join(BRAIN_DIR, "brand_story_1789646217204.jpg")
IMG_LOGO = os.path.join(BRAIN_DIR, ".tempmediaStorage", "media_1789648850789.jpg")

print("Updating Categories with High-Res AI Images...")

# 1. Update Categories
cat_map = {
    'daily-essentials': IMG_DAILY,
    'royal-heritage': IMG_ROYAL,
    'street-food': IMG_STREET,
    'regional-curries': IMG_BRAND,
}

for slug, img_path in cat_map.items():
    try:
        cat = Category.objects.get(slug=slug)
        with open(img_path, 'rb') as f:
            cat.image.save(f"{slug}.jpg", File(f), save=True)
        print(f"Updated category: {cat.name} -> {cat.image.url}")
    except Exception as e:
        print(f"Error updating category {slug}: {e}")

# Helper to create luxury product photo
def create_luxury_product_card(base_img_path, title, subtitle, badge_text, out_path, crop_box=None):
    base = Image.open(base_img_path).convert('RGBA')
    if crop_box:
        base = base.crop(crop_box)
    
    # Resize / square crop
    w, h = base.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    base = base.crop((left, top, left + min_dim, top + min_dim))
    base = base.resize((1000, 1000), Image.Resampling.LANCZOS)
    
    # Slight contrast / vibrance enhancement
    enhancer = ImageEnhance.Color(base)
    base = enhancer.enhance(1.1)
    
    # Overlay gradient at bottom for text contrast
    overlay = Image.new('RGBA', (1000, 1000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Bottom scrim
    for y in range(650, 1000):
        alpha = int(((y - 650) / 350.0) ** 1.5 * 210)
        draw.line([(0, y), (1000, y)], fill=(20, 10, 5, alpha))
        
    # Top vignette for luxury feel
    for y in range(0, 200):
        alpha = int(((200 - y) / 200.0) * 110)
        draw.line([(0, y), (1000, y)], fill=(10, 5, 2, alpha))
        
    base = Image.alpha_composite(base, overlay)
    
    # Add Gold/Maroon Badge at top right
    if badge_text:
        badge_overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0))
        b_draw = ImageDraw.Draw(badge_overlay)
        
        # Badge rounded pill
        bx0, by0, bx1, by1 = 660, 45, 955, 95
        b_draw.rounded_rectangle([bx0, by0, bx1, by1], radius=25, fill=(139, 26, 26, 240), outline=(234, 179, 8, 240), width=2)
        
        # Text
        try:
            font_badge = ImageFont.truetype("arial.ttf", 26)
        except:
            font_badge = ImageFont.load_default()
            
        b_draw.text(((bx0 + bx1) / 2, (by0 + by1) / 2), badge_text, fill=(255, 250, 240), anchor="mm", font=font_badge)
        base = Image.alpha_composite(base, badge_overlay)

    # Add Logo small at top left
    if os.path.exists(IMG_LOGO):
        try:
            logo = Image.open(IMG_LOGO).convert('RGBA')
            logo.thumbnail((180, 110), Image.Resampling.LANCZOS)
            base.paste(logo, (45, 35), mask=logo)
        except Exception as e:
            pass

    # Bottom labels
    text_overlay = Image.new('RGBA', (1000, 1000), (0,0,0,0))
    t_draw = ImageDraw.Draw(text_overlay)
    
    try:
        font_sub = ImageFont.truetype("arial.ttf", 24)
        font_title = ImageFont.truetype("georgia.ttf", 46)
    except:
        font_sub = ImageFont.load_default()
        font_title = ImageFont.load_default()
        
    t_draw.text((50, 830), subtitle.upper(), fill=(234, 179, 8, 255), font=font_sub)
    t_draw.text((50, 880), title, fill=(255, 255, 255, 255), font=font_title)
    
    # Thin gold accent line
    t_draw.line([(50, 865), (220, 865)], fill=(234, 179, 8, 200), width=3)
    
    base = Image.alpha_composite(base, text_overlay)
    base = base.convert('RGB')
    base.save(out_path, quality=92)
    print(f"Created luxury product image: {out_path}")

# Generate luxury images for combos and bestsellers
out_dir = os.path.join(BRAIN_DIR, "scratch", "generated_media")
os.makedirs(out_dir, exist_ok=True)

# 2. Fixed Combo: Panch Ratna
combo_img_path = os.path.join(out_dir, "combo_panch_ratna.jpg")
create_luxury_product_card(
    IMG_DAILY, 
    "Panch Ratna 5-Masala Box", 
    "SIGNATURE KITCHEN GIFT SET", 
    "FREE All-In-One", 
    combo_img_path
)

try:
    combo = FixedCombo.objects.get(slug="panch-ratna-daily-essential-box")
    with open(combo_img_path, 'rb') as f:
        combo.image.save("panch-ratna-box.jpg", File(f), save=True)
    print("Updated Panch Ratna Combo image!")
except Exception as e:
    print(f"Error combo: {e}")

# 3. Top Bestsellers
bestsellers_config = [
    {
        "slug": "all-in-one-magic-masala",
        "src": IMG_DAILY,
        "title": "All-In-One Magic Masala",
        "sub": "Stone-Ground · 15 Whole Spices",
        "badge": "#1 BESTSELLER"
    },
    {
        "slug": "mu-peri-peri-magic-sprinkle",
        "src": IMG_STREET,
        "title": "Peri Peri Magic Sprinkle",
        "sub": "Fiery Heat · Gourmet Herbs",
        "badge": "HOT & CRISP"
    },
    {
        "slug": "mu-tangy-delhi-chaat-masala",
        "src": IMG_STREET,
        "title": "Tangy Delhi Chaat Masala",
        "sub": "Amchur & Black Salt Rock",
        "badge": "4.9 RATED"
    },
    {
        "slug": "mu-hyderabadi-dum-biryani-masala",
        "src": IMG_ROYAL,
        "title": "Hyderabadi Dum Biryani Masala",
        "sub": "Shahi Saffron & Cardamom",
        "badge": "ROYAL HERITAGE"
    },
    {
        "slug": "mu-mumbai-pav-bhaji-masala",
        "src": IMG_STREET,
        "title": "Mumbai Pav Bhaji Masala",
        "sub": "Chowpatty Style Authentic",
        "badge": "STREET SPECIAL"
    },
    {
        "slug": "mu-royal-garam-masala",
        "src": IMG_ROYAL,
        "title": "MU Royal Garam Masala",
        "sub": "Pure Whole Spices · High Aroma",
        "badge": "HAND-CRAFTED"
    }
]

for cfg in bestsellers_config:
    try:
        p = Product.objects.get(slug=cfg["slug"])
        out_p = os.path.join(out_dir, f"{cfg['slug']}.jpg")
        create_luxury_product_card(cfg["src"], cfg["title"], cfg["sub"], cfg["badge"], out_p)
        with open(out_p, 'rb') as f:
            p.main_image.save(f"{cfg['slug']}.jpg", File(f), save=True)
        print(f"Updated product image for: {p.name}")
    except Exception as e:
        print(f"Error product {cfg['slug']}: {e}")

print("All database images successfully updated!")

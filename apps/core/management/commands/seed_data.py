"""
apps/core/management/commands/seed_data.py
Populates the database with realistic demo data for MU Magic Masala:
- SiteSettings singleton
- Admin superuser and demo customer
- Product Categories, Tags, and Products with variants and images
- Fixed Combos and Customizable Combo rules
- CMS content (Hero slides, Announcement bar, Testimonials, FAQs, Blog posts, Static pages)
- Customer reviews
"""

import os
from decimal import Decimal
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.catalog.models import Category, Tag, Product, ProductVariant, ProductImage
from apps.combos.models import FixedCombo, FixedComboItem, CustomizeComboRule
from apps.cms.models import HeroSlide, AnnouncementBar, Banner, Testimonial, FAQItem, StaticPage, BlogPost
from apps.reviews.models import ProductReview
from apps.accounts.models import CustomerProfile, Address

User = get_user_model()


def make_placeholder_image(width, height, bg_color, text, text_color="#FFFFFF"):
    """Generates an in-memory JPEG image with PIL."""
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw a subtle decorative border
    draw.rectangle([10, 10, width - 10, height - 10], outline=text_color, width=2)
    
    # Center text approximation
    font_size = max(18, min(width, height) // 14)
    # PIL default font fallback
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Draw centered title
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (width - tw) // 2
    ty = (height - th) // 2
    draw.text((tx, ty), text, fill=text_color, font=font)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


class Command(BaseCommand):
    help = "Seeds the database with full realistic demo data for MU Magic Masala"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding MU Magic Masala demo data..."))

        # 1. Site Settings
        settings = SiteSettings.get_solo()
        settings.brand_name = "MU Magic Masala"
        settings.support_phone = "+91 9410265521"
        settings.support_email = "Mahilaudyogmagic@gmail.com"
        settings.whatsapp_number = "+919410265521"
        settings.address = "MOHALLA MOHAN, CHITRAGUPT COLONY, PULIYA NO. 3, KASGANJ, Kanshiramnagar, Uttar Pradesh - 207123"
        settings.manufacturer_address = "MOHALLA MOHAN, CHITRAGUPT COLONY, PULIYA NO. 3, KASGANJ, Kanshiramnagar, Uttar Pradesh - 207123"
        settings.legal_firm_name = "Mahila Udyog"
        settings.min_order_value = Decimal("199.00")
        settings.cod_charge = Decimal("50.00")
        settings.cod_advance_percent = Decimal("50.00")
        settings.free_shipping_threshold = Decimal("499.00")
        settings.fixed_combo_item_count = 5
        settings.customize_combo_item_count = 10
        settings.customize_combo_price = Decimal("999.00")
        settings.fssai_license_number = "12723058000110"
        settings.meta_title = "MU Magic Masala — Stone Ground Artisanal Spices & Blends"
        settings.meta_description = "Handcrafted Indian spice blends roasted in small batches with zero preservatives. Pure heritage aroma in every pinch."
        settings.instagram_url = "https://instagram.com/mumagicmasala"
        settings.facebook_url = "https://facebook.com/mumagicmasala"
        settings.youtube_url = "https://youtube.com/@mumagicmasala"
        settings.save()
        self.stdout.write(self.style.SUCCESS("[OK] SiteSettings configured"))

        # 2. Users
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@mumagicmasala.com", "first_name": "Admin", "last_name": "Owner", "is_staff": True, "is_superuser": True}
        )
        if created:
            admin_user.set_password("adminpassword123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("[OK] Created superuser: admin / adminpassword123"))

        cust_user, _ = User.objects.get_or_create(
            username="priya_sharma",
            defaults={"email": "priya.sharma@example.com", "first_name": "Priya", "last_name": "Sharma"}
        )
        cust_user.set_password("customerpassword123")
        cust_user.save()

        profile, _ = CustomerProfile.objects.get_or_create(
            user=cust_user,
            defaults={"phone": "+919876500001"}
        )
        Address.objects.get_or_create(
            user=cust_user,
            is_default=True,
            defaults={
                "full_name": "Priya Sharma",
                "phone": "+919876500001",
                "address_line1": "Flat 402, Royal Palms Apartments",
                "address_line2": "Near HSR Club, Sector 2",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560102",
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Created demo customer: priya.sharma@example.com"))

        # 3. Tags
        tag_names = ["Bestseller", "Pure Jain Friendly", "Low Heat", "Fiery Hot", "Small Batch", "100% Natural", "No Onion No Garlic"]
        tags = {}
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags[name] = t

        # 4. Categories
        cat_data = [
            ("Daily Essentials", "daily-essentials", "#B91C1C", "Everyday pantry staples freshly milled from whole spices.", 1),
            ("Royal Heritage Blends", "royal-heritage", "#92400E", "Regal slow-roasted Mughlai and Awadhi spice secret blends.", 2),
            ("Street Food & Snacks", "street-food", "#C2410C", "Tangy, zesty and vibrant street blends for chaat and snacks.", 3),
            ("Regional Curries", "regional-curries", "#15803D", "Authentic coastal, Chettinad, and regional curry marvels.", 4),
        ]
        categories = {}
        for cname, cslug, color, cdesc, order in cat_data:
            cat, created = Category.objects.get_or_create(
                slug=cslug,
                defaults={
                    "name": cname,
                    "description": f"<p>{cdesc}</p>",
                    "display_order": order,
                    "meta_title": f"{cname} — MU Magic Masala",
                    "meta_description": cdesc,
                }
            )
            if not cat.image:
                buf = make_placeholder_image(600, 600, color, cname)
                cat.image.save(f"{cslug}.jpg", ContentFile(buf.getvalue()), save=True)
            categories[cslug] = cat
        self.stdout.write(self.style.SUCCESS("[OK] Created categories"))

        # 5. Products
        products_data = [
            {
                "name": "MU Royal Garam Masala",
                "slug": "mu-royal-garam-masala",
                "category": "royal-heritage",
                "sku": "MU-RGM-01",
                "price": Decimal("149.00"),
                "mrp": Decimal("199.00"),
                "stock": 45,
                "color": "#78350F",
                "is_featured": True,
                "is_bestseller": True,
                "short_desc": "Hand-pounded blend of 18 whole spices, slow roasted over low flames.",
                "desc": "<h3>The King of All Spice Blends</h3><p>Our Royal Garam Masala is roasted in small iron kadhais using centuries-old techniques. Loaded with green cardamom, Kashmiri shahi jeera, mace, cinnamon, and stone flower (dagad phool) for unmatched aromatic warmth.</p><h4>Key Highlights:</h4><ul><li>No added starches or anti-caking agents</li><li>Contains real javitri and wild dagad phool</li><li>Rich in essential aromatic oils</li></ul>",
                "tags": ["Bestseller", "Small Batch", "100% Natural"],
                "variants": [("100g", Decimal("149.00"), Decimal("199.00"), 45, "MU-RGM-100G"), ("250g", Decimal("329.00"), Decimal("449.00"), 30, "MU-RGM-250G")],
            },
            {
                "name": "MU Mumbai Pav Bhaji Masala",
                "slug": "mu-mumbai-pav-bhaji-masala",
                "category": "street-food",
                "sku": "MU-PB-01",
                "price": Decimal("119.00"),
                "mrp": Decimal("149.00"),
                "stock": 8, # Low stock indicator demo!
                "color": "#9A3412",
                "is_featured": True,
                "is_bestseller": True,
                "short_desc": "Chowpatty-style buttery tangy richness with roasted Byadgi chili and amchur.",
                "desc": "<h3>Relive the Streets of Juhu & Chowpatty</h3><p>Crafted to give that signature deep red hue without synthetic food dyes. Rich in sweet Byadgi chillies, kasuri methi, dry mango, and stone-roasted coriander seeds.</p>",
                "tags": ["Bestseller", "100% Natural"],
                "variants": [("100g", Decimal("119.00"), Decimal("149.00"), 8, "MU-PB-100G"), ("250g", Decimal("269.00"), Decimal("349.00"), 20, "MU-PB-250G")],
            },
            {
                "name": "MU Hyderabadi Dum Biryani Masala",
                "slug": "mu-hyderabadi-dum-biryani-masala",
                "category": "royal-heritage",
                "sku": "MU-HBM-01",
                "price": Decimal("169.00"),
                "mrp": Decimal("225.00"),
                "stock": 35,
                "color": "#831843",
                "is_featured": True,
                "is_bestseller": True,
                "short_desc": "Nizami secret recipe with saffron notes, star anise, and toasted black cumin.",
                "desc": "<h3>Pure Nizami Elegance</h3><p>Takes your chicken, mutton, or jackfruit dum biryani straight to royal banquet tier. Ground with crushed bay leaves, star anise, nutmeg, and Persian saffron strands.</p>",
                "tags": ["Bestseller", "Small Batch"],
                "variants": [("100g", Decimal("169.00"), Decimal("225.00"), 35, "MU-HBM-100G"), ("250g", Decimal("379.00"), Decimal("499.00"), 15, "MU-HBM-250G")],
            },
            {
                "name": "MU Magic All-Purpose Kitchen King",
                "slug": "mu-kitchen-king-masala",
                "category": "daily-essentials",
                "sku": "MU-KK-01",
                "price": Decimal("129.00"),
                "mrp": Decimal("165.00"),
                "stock": 50,
                "color": "#854D0E",
                "is_featured": True,
                "is_bestseller": False,
                "short_desc": "The one masala that elevates paneer, dals, and mixed vegetable curries effortlessly.",
                "desc": "<h3>Your Everyday Culinary Wingman</h3><p>A harmonious balance of turmeric, fenugreek, coriander, cumin, ginger, and gentle yellow mustard. Adds instant restaurant-style depth to everyday home gravies.</p>",
                "tags": ["100% Natural", "Pure Jain Friendly"],
                "variants": [("100g", Decimal("129.00"), Decimal("165.00"), 50, "MU-KK-100G"), ("250g", Decimal("289.00"), Decimal("375.00"), 25, "MU-KK-250G")],
            },
            {
                "name": "MU Tangy Delhi Chaat Masala",
                "slug": "mu-tangy-delhi-chaat-masala",
                "category": "street-food",
                "sku": "MU-DCM-01",
                "price": Decimal("99.00"),
                "mrp": Decimal("130.00"),
                "stock": 60,
                "color": "#713F12",
                "is_featured": False,
                "is_bestseller": True,
                "short_desc": "Zingy black salt, dried pomegranate seeds (anardana), and sun-dried mint.",
                "desc": "<h3>Chatpata Perfection</h3><p>Sprinkle over cut fruits, roasted nuts, dahi bhalla, or crispy parathas for an addictive punch of tangy umami flavor.</p>",
                "tags": ["Pure Jain Friendly", "100% Natural"],
                "variants": [("100g", Decimal("99.00"), Decimal("130.00"), 60, "MU-DCM-100G")],
            },
            {
                "name": "MU Malabar Curry Masala",
                "slug": "mu-malabar-curry-masala",
                "category": "regional-curries",
                "sku": "MU-MCM-01",
                "price": Decimal("139.00"),
                "mrp": Decimal("180.00"),
                "stock": 25,
                "color": "#166534",
                "is_featured": False,
                "is_bestseller": False,
                "short_desc": "Toasted coconut flakes, curry leaves, tellicherry black pepper, and fennel.",
                "desc": "<h3>Southern Coastal Magic</h3><p>Infused with sun-dried Malabar curry leaves, toasted coconut, black pepper, and fennel for rich, fragrant South Indian stew and curry wonders.</p>",
                "tags": ["Small Batch", "100% Natural"],
                "variants": [("100g", Decimal("139.00"), Decimal("180.00"), 25, "MU-MCM-100G")],
            },
            {
                "name": "MU Peri Peri Magic Sprinkle",
                "slug": "mu-peri-peri-magic-sprinkle",
                "category": "street-food",
                "sku": "MU-PPM-01",
                "price": Decimal("109.00"),
                "mrp": Decimal("145.00"),
                "stock": 30,
                "color": "#B91C1C",
                "is_featured": False,
                "is_bestseller": True,
                "short_desc": "Fiery African bird's eye chili, roasted garlic, sweet paprika, and herbs.",
                "desc": "<h3>Upgrade Your Fries, Popcorn & Pizzas</h3><p>A spicy, zesty twist crafted for modern snacking. Shake it over hot french fries, buttered popcorn, or grilled paneer cubes.</p>",
                "tags": ["Fiery Hot"],
                "variants": [("80g", Decimal("109.00"), Decimal("145.00"), 30, "MU-PPM-80G")],
            },
            {
                "name": "MU Kashmiri Dum Aloo Masala",
                "slug": "mu-kashmiri-dum-aloo-masala",
                "category": "regional-curries",
                "sku": "MU-KDA-01",
                "price": Decimal("129.00"),
                "mrp": Decimal("160.00"),
                "stock": 20,
                "color": "#991B1B",
                "is_featured": False,
                "is_bestseller": False,
                "short_desc": "Authentic sonth (dry ginger) and saunf (fennel) forward Kashmiri culinary legacy.",
                "desc": "<h3>Traditional Valley Flavors</h3><p>No garlic, no onion needed. The authentic Kashmiri dum aloo flavor profile relies purely on dried ginger powder, fennel, and deep crimson Kashmiri chillies.</p>",
                "tags": ["No Onion No Garlic", "Pure Jain Friendly"],
                "variants": [("100g", Decimal("129.00"), Decimal("160.00"), 20, "MU-KDA-100G")],
            },
        ]

        created_products = []
        for pdata in products_data:
            cat = categories[pdata["category"]]
            prod, created = Product.objects.get_or_create(
                slug=pdata["slug"],
                defaults={
                    "name": pdata["name"],
                    "category": cat,
                    "sku": pdata["sku"],
                    "price": pdata["price"],
                    "mrp": pdata["mrp"],
                    "stock_quantity": pdata["stock"],
                    "short_description": pdata["short_desc"],
                    "description": pdata["desc"],
                    "is_featured": pdata["is_featured"],
                    "is_bestseller": pdata["is_bestseller"],
                    "is_customize_combo_eligible": True,
                    "meta_title": f"{pdata['name']} | Buy Online — MU Magic Masala",
                    "meta_description": pdata["short_desc"],
                }
            )
            for tname in pdata["tags"]:
                prod.tags.add(tags[tname])

            if not prod.main_image:
                buf = make_placeholder_image(1200, 1200, pdata["color"], prod.name)
                prod.main_image.save(f"{prod.slug}.jpg", ContentFile(buf.getvalue()), save=True)

            # Variants
            for label, price, mrp, stock, vsku in pdata["variants"]:
                ProductVariant.objects.get_or_create(
                    product=prod,
                    size_label=label,
                    defaults={"price": price, "mrp": mrp, "stock_quantity": stock, "sku": vsku}
                )

            # Reviews
            ProductReview.objects.get_or_create(
                product=prod,
                user=cust_user,
                defaults={
                    "rating": 5,
                    "title": "Incredible freshness and aroma!",
                    "comment": f"I used this in my Sunday cooking and the aroma filled the entire home. You can distinctly taste that these are freshly ground without artificial filler.",
                    "is_approved": True,
                }
            )
            created_products.append(prod)

        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(created_products)} products with variants & reviews"))

        # 6. Fixed Combos
        combo1, _ = FixedCombo.objects.get_or_create(
            slug="panch-ratna-daily-essential-box",
            defaults={
                "name": "The Panch Ratna 5-Masala Starter Box",
                "combo_price": Decimal("499.00"),
                "description": "Our 5 most beloved spice blends bundled together for the ultimate kitchen upgrade. Includes Royal Garam Masala, Pav Bhaji, Dum Biryani, Kitchen King, and Delhi Chaat Masala.",
                "meta_title": "The Panch Ratna Starter Box — MU Magic Masala",
                "meta_description": "Get 5 top-rated artisanal spice blends at an exclusive bundle savings.",
            }
        )
        if not combo1.image:
            buf = make_placeholder_image(1200, 1200, "#7F1D1D", "Panch Ratna 5-Pack")
            combo1.image.save("panch-ratna.jpg", ContentFile(buf.getvalue()), save=True)

        for p in created_products[:5]:
            FixedComboItem.objects.get_or_create(combo=combo1, product=p, defaults={"quantity": 1})

        self.stdout.write(self.style.SUCCESS("[OK] Created Fixed Combo"))

        # 7. Customizable Combo Rule
        rule, _ = CustomizeComboRule.objects.get_or_create(
            name="Build Your Own 5-Masala Box",
            defaults={
                "required_item_count": 5,
                "fixed_price": Decimal("499.00"),
                "eligible_mode": CustomizeComboRule.EligibleMode.AUTO,
                "price_cap": Decimal("199.00"),
                "is_active": True,
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Created Customizable Combo Rule (5 items for Rs 499)"))

        # 8. CMS: Announcement Bar
        AnnouncementBar.objects.get_or_create(
            message="FREE Shipping across India on orders above Rs 499 | Small-batch stone ground spices",
            defaults={
                "background_color": "#7C1E1E",
                "text_color": "#FFFFFF",
                "is_active": True,
                "display_order": 1,
            }
        )

        # 9. CMS: Hero Slides
        slide1, _ = HeroSlide.objects.get_or_create(
            title="Aromatic Heritage in Every Pinch",
            defaults={
                "subtitle": "Small-batch stone ground Indian spice blends with zero preservatives, pure essential oils, and unforgettable flavor.",
                "cta_text": "Explore All Masalas",
                "cta_link": "/shop/",
                "display_order": 1,
                "is_active": True,
            }
        )
        if not slide1.desktop_image:
            buf = make_placeholder_image(1920, 800, "#451A03", "MU Magic Masala — Artisanal Blends")
            slide1.desktop_image.save("hero1-desktop.jpg", ContentFile(buf.getvalue()), save=True)

        # 10. CMS: Testimonials
        testimonials_data = [
            ("Chef Vikram Merchant", 5, "The aroma of MU Magic Royal Garam Masala reminds me of my grandmother's hand-ground spices in Lucknow. It has genuine depth and no stale chalkiness."),
            ("Dr. Meera Iyer", 5, "I love that their ingredients list contains ZERO fillers, starch, or artificial coloring. You get pure honest spices. My family's Sunday curries have leveled up!"),
            ("Rohit Verma", 5, "The Mumbai Pav Bhaji and Peri Peri sprinkles are sensational. Fast delivery and the advance COD checkout was completely hassle-free."),
        ]
        for name, rating, text in testimonials_data:
            Testimonial.objects.get_or_create(
                customer_name=name,
                defaults={"rating": rating, "text": text, "is_active": True}
            )

        # 11. CMS: FAQs
        faqs_data = [
            ("What makes MU Magic Masala different from market brands?", "<p>Market spices are machine-ground at high temperatures, which burns off volatile essential oils. We slow roast spices over mild heat and stone grind in micro-batches to preserve 100% of the natural aromas and curative botanical oils.</p>"),
            ("Do you use any preservatives, MSG, or artificial food color?", "<p>Absolutely none. We never add starch, anti-caking agents, synthetic food colors, or chemical preservatives. What you see on our ingredient list is 100% whole spices.</p>"),
            ("How does Cash on Delivery (COD) work on your store?", "<p>To prevent fake delivery orders and ensure doorstep safety, we collect a small 50% advance online via UPI or Cards. The remaining 50% plus a nominal Rs 50 COD courier handling charge is payable in cash upon delivery.</p>"),
            ("What is the shelf life of the spices?", "<p>Because our masalas are freshly ground with high essential oil concentrations, they remain at peak aroma for 12 months from manufacture. Store in an airtight container away from direct sunlight.</p>"),
        ]
        for q, a in faqs_data:
            FAQItem.objects.get_or_create(question=q, defaults={"answer": a, "is_active": True})

        # 12. CMS: Static Pages
        pages_data = [
            ("About Us", "about-us", "<h2>Our Story: Born in the Heart of Khari Baoli</h2><p>MU Magic Masala began with a simple observation: modern commercial spices have lost their soul. Mass industrial grinding burns away the precious volatile oils that give Indian dishes their intoxicating aroma.</p><p>We partner directly with certified spice farmers in Malabar, Salem, Guntur, and Kashmir. Every blend is roasted in small batches and stone-milled to perfection.</p>"),
            ("Shipping & Returns", "shipping-returns", "<h2>Fast, Reliable Pan-India Delivery</h2><p>Orders are dispatched within 24 hours via premium courier partners. Delivery takes 2-4 business days for metro cities and 4-6 days for rest of India. We offer free delivery on orders above Rs 499.</p><h3>Damage Guarantee</h3><p>If your package arrives damaged, take a photo and WhatsApp us within 48 hours for an instant replacement.</p>"),
            ("Privacy Policy", "privacy-policy", "<h2>Your Privacy Matters</h2><p>MU Magic Masala does not sell or lease customer contact details. We store only essential data required to fulfill orders and send tracking notifications via SMS and WhatsApp.</p>"),
            ("Terms of Service", "terms-of-service", "<h2>Terms & Conditions</h2><p>All prices listed on mumagicmasala.com are in Indian Rupees (INR) inclusive of applicable GST taxes. We reserve the right to cancel orders with incorrect pricing or fraudulent payment attempts.</p>"),
        ]
        for title, slug, content in pages_data:
            StaticPage.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "content": content, "meta_title": f"{title} — MU Magic Masala"}
            )

        # 13. CMS: Blog Posts
        blog_data = [
            (
                "The Science of Tempering: Why Stone-Ground Spices Smell Superior",
                "science-of-tempering-stone-ground-spices",
                "<p>Have you ever wondered why tadka smells so heavenly? When whole spices meet hot ghee, the botanical cellular walls rupture, releasing aroma molecules. Factory roller mills generate high friction heat that evaporates these volatile terpenes before the spice ever reaches your jar.</p><p>By contrast, our traditional slow cold-grinding keeps temperatures below 38°C, keeping 40% more aromatic richness intact.</p>",
                "Explore the chemistry behind why small-batch stone ground spices elevate your cooking."
            ),
            (
                "Mastering the Perfect Hyderabadi Dum Biryani at Home",
                "mastering-hyderabadi-dum-biryani-home",
                "<p>Dum cooking is the art of sealing meat and par-cooked basmati rice with dough so steam cannot escape. The secret is layering freshly ground garam masala with fried brown onions (birista) and crushed mint leaves.</p><p>Follow this step-by-step masterclass to achieve restaurant-quality grain separation and exquisite scent.</p>",
                "Step-by-step masterclass on slow cooking the ultimate Nizami feast at home."
            ),
        ]
        for title, slug, content, desc in blog_data:
            b, created = BlogPost.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "content": content,
                    "meta_description": desc,
                    "published_at": timezone.now(),
                }
            )
            if not b.featured_image:
                buf = make_placeholder_image(1200, 630, "#78350F", title[:30])
                b.featured_image.save(f"{slug}.jpg", ContentFile(buf.getvalue()), save=True)

        self.stdout.write(self.style.SUCCESS("[OK] Created CMS pages, FAQs, testimonials, and blog articles"))
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(self.style.SUCCESS("MU MAGIC MASALA DATABASE SEEDED SUCCESSFULLY!"))
        self.stdout.write(self.style.SUCCESS("=================================================="))

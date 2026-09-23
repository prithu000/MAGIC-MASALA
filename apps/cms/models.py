"""
apps/cms/models.py
HeroSlide, AnnouncementBar, Banner, Testimonial, FAQItem, StaticPage, BlogPost, HomepageAssemblySection
"""

import re
from ckeditor.fields import RichTextField
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill, ResizeToFit

from apps.core.validators import validate_image_size, validate_image_type, validate_video_size


def clean_reel_url(raw_url: str):
    """
    Intelligently parse ANY Instagram or YouTube Reel/Short/Video URL,
    including raw links, mobile share links, query params, and iframe codes,
    and convert into a clean, embeddable URL while detecting the platform.
    """
    if not raw_url:
        return "", "other"

    url = raw_url.strip()

    # If pasted iframe code e.g. <iframe src="...">
    iframe_match = re.search(r'src=["\']([^"\']+)["\']', url)
    if iframe_match:
        url = iframe_match.group(1)

    # 1. Instagram: /reel/CODE, /reels/CODE, /p/CODE
    insta_match = re.search(r'instagram\.com/(?:reel|reels|p)/([A-Za-z0-9_-]+)', url)
    if insta_match:
        code = insta_match.group(1)
        return f"https://www.instagram.com/reel/{code}/embed/", "instagram"

    # 2. YouTube Shorts / Watch / youtu.be / embed
    yt_match = re.search(
        r'(?:youtube\.com/(?:shorts/|watch\?v=|embed/)|youtu\.be/)([A-Za-z0-9_-]{10,12})',
        url,
    )
    if yt_match:
        video_id = yt_match.group(1)
        return f"https://www.youtube.com/embed/{video_id}", "youtube"

    # Generic fallbacks
    if "instagram.com" in url:
        clean = url.split("?")[0].rstrip("/")
        if not clean.endswith("/embed"):
            clean = clean + "/embed/"
        return clean, "instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        return url, "youtube"

    return url, "other"


class HeroSlide(models.Model):
    class Placement(models.TextChoices):
        HOMEPAGE = "home", "Homepage"
        COMBOS = "combos", "Combos Page"
        BUILD_COMBO = "build_combo", "Build Your Own Combo Page"

    placement = models.CharField(
        max_length=20,
        choices=Placement.choices,
        default=Placement.HOMEPAGE,
        help_text="Choose which page this hero slide will appear on.",
    )
    title = models.CharField(max_length=200, blank=True, default="", help_text="Slide heading. Leave blank or uncheck 'show text overlay' if your image already has text.")
    subtitle = models.CharField(max_length=300, blank=True, default="")
    show_text_overlay = models.BooleanField(
        default=True,
        help_text="Show text overlay, subtitle, and CTA button over the image. Uncheck this if your uploaded banner graphic already has text designed on it."
    )
    desktop_image = ProcessedImageField(
        upload_to="hero/desktop/",
        processors=[ResizeToFit(1920, 500)],
        format="JPEG",
        options={"quality": 90},
        validators=[validate_image_size, validate_image_type],
        help_text="Desktop Banner Size: 1920 × 500 px. Sleek, professional full-width banner format.",
    )
    mobile_image = ProcessedImageField(
        upload_to="hero/mobile/",
        processors=[ResizeToFit(1080, 600)],
        format="JPEG",
        options={"quality": 88},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Mobile Banner Size: 1080 × 600 px. Compact mobile banner format.",
    )
    cta_text = models.CharField(max_length=80, blank=True, help_text='Button label, e.g. "Shop Now"')
    cta_link = models.CharField(max_length=200, blank=True, help_text='URL the button or entire banner links to, e.g. "/combos/build/"')
    display_order = models.PositiveSmallIntegerField(default=0)
    start_datetime = models.DateTimeField(
        null=True, blank=True, help_text="Leave blank to show immediately when activated."
    )
    end_datetime = models.DateTimeField(
        null=True, blank=True, help_text="Leave blank to show indefinitely."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["placement", "display_order"]

    def __str__(self):
        return f"[{self.get_placement_display()}] {self.title}"


class AnnouncementBar(models.Model):
    message = models.CharField(max_length=300, help_text="The text shown in the announcement bar.")
    background_color = models.CharField(
        max_length=7, default="#7C1E1E", help_text="Hex color code, e.g. #7C1E1E"
    )
    text_color = models.CharField(max_length=7, default="#FFFFFF", help_text="Hex color code, e.g. #FFFFFF")
    link_url = models.CharField(max_length=200, blank=True, help_text="Optional — makes the whole bar clickable.")
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.message[:80]


class Banner(models.Model):
    class Placement(models.TextChoices):
        HOMEPAGE = "homepage", "Homepage"
        CATEGORY = "category", "Category Pages"
        CHECKOUT = "checkout", "Checkout"

    image = ProcessedImageField(
        upload_to="banners/",
        processors=[ResizeToFit(1200, 400)],
        format="JPEG",
        options={"quality": 85},
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 1200×400 px. Auto-resized on upload.",
    )
    link_url = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    placement = models.CharField(max_length=15, choices=Placement.choices, default=Placement.HOMEPAGE)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"Banner — {self.get_placement_display()}"


class Testimonial(models.Model):
    customer_name = models.CharField(max_length=100)
    photo = ProcessedImageField(
        upload_to="testimonials/",
        processors=[ResizeToFill(300, 300)],
        format="JPEG",
        options={"quality": 80},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Optional. Recommended: 300×300 px (square), JPG/WebP.",
    )
    rating = models.PositiveSmallIntegerField(default=5, help_text="Rating out of 5.")
    text = models.TextField(help_text="The customer's review text.")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.customer_name} — {self.rating}★"


class FAQItem(models.Model):
    question = models.CharField(max_length=300)
    answer = RichTextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order"]
        verbose_name = "FAQ Item"

    def __str__(self):
        return self.question


class StaticPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    content = RichTextField(help_text="Full page content. Use the rich-text editor — no HTML knowledge needed.")
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("cms:static_page", kwargs={"slug": self.slug})


class BlogPost(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    featured_image = ProcessedImageField(
        upload_to="blog/",
        processors=[ResizeToFit(1200, 630)],
        format="JPEG",
        options={"quality": 85},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 1200×630 px (also used as social share image). Auto-resized on upload.",
    )
    featured_image_alt = models.CharField(max_length=200, blank=True)
    content = RichTextField()
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)
    published_at = models.DateTimeField(
        null=True, blank=True, help_text="Leave blank to save as draft. Set to publish."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("cms:blog_detail", kwargs={"slug": self.slug})

    @property
    def is_published(self):
        from django.utils import timezone
        return self.published_at is not None and self.published_at <= timezone.now()


class InfluencerReel(models.Model):
    """
    Admin-managed influencer reel/video section on the homepage.
    Admin pastes ANY YouTube Short/Video or Instagram Reel URL,
    and the system automatically detects platform and formats embed.
    """

    influencer_name = models.CharField(
        max_length=100,
        help_text="Full name of the creator/influencer, e.g. Priya Sharma",
    )
    handle = models.CharField(
        max_length=100,
        blank=True,
        help_text="Social handle, e.g. @priyafoodie",
    )
    thumbnail = ProcessedImageField(
        upload_to="influencer_reels/",
        processors=[ResizeToFill(600, 800)],
        format="JPEG",
        options={"quality": 85},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Optional cover image for the reel. Recommended: 600×800 px portrait.",
    )
    video_file = models.FileField(
        upload_to="influencer_reels/videos/",
        null=True,
        blank=True,
        validators=[validate_video_size],
        help_text="Optional: Upload an MP4 video directly (recommended for 100% reliable mobile playback without third-party iframe blocks).",
    )
    embed_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=(
            "Paste ANY Instagram Reel link (e.g. https://www.instagram.com/reel/C8.../) "
            "or YouTube Short / Video link (e.g. https://youtube.com/shorts/...). "
            "Auto-converted to embed format on save."
        ),
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short caption shown on the card, e.g. 'This masala changed my biryani game!'",
    )
    platform = models.CharField(
        max_length=20,
        choices=[
            ("instagram", "Instagram"),
            ("youtube", "YouTube"),
            ("video", "Direct Video (MP4)"),
            ("other", "Other"),
        ],
        default="instagram",
        help_text="Auto-detected from URL, or select manually.",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]
        verbose_name = "Influencer Reel"
        verbose_name_plural = "Influencer Reels"

    def __str__(self):
        return f"{self.influencer_name} ({self.handle or 'no handle'}) [{self.get_platform_display()}]"

    @property
    def instagram_permalink(self):
        if self.platform == "instagram" and self.embed_url:
            match = re.search(r'instagram\.com/(?:reel|reels|p)/([A-Za-z0-9_-]+)', self.embed_url)
            if match:
                return f"https://www.instagram.com/reel/{match.group(1)}/"
            return self.embed_url.replace('/embed/', '/')
        return self.embed_url

    def clean(self):
        if self.embed_url:
            cleaned_url, detected = clean_reel_url(self.embed_url)
            self.embed_url = cleaned_url
            if detected != "other":
                self.platform = detected
        elif self.video_file:
            self.platform = "video"

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class HomepageAssemblySection(models.Model):
    """
    Singleton model — controls the final hero image shown at the end of the
    scroll-driven 10-Spice assembly experience on the homepage.
    Only ONE record should exist. Admin can upload/change the image at any time.
    """

    hero_image = ProcessedImageField(
        upload_to="assembly/",
        processors=[ResizeToFit(1200, 675)],
        format="JPEG",
        options={"quality": 88},
        validators=[validate_image_size, validate_image_type],
        help_text=(
            "Assembly Section Hero Image (Final Reveal Card). "
            "Recommended size: 1200 × 675 px (16:9 ratio). "
            "This image is shown inside the dark combo reveal card when the user finishes scrolling through the assembly section."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide the custom image and use the default assembled pack photo.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Homepage Assembly Section"
        verbose_name_plural = "Homepage Assembly Section"

    def __str__(self):
        return "Homepage Assembly Section Hero Image"

    def save(self, *args, **kwargs):
        # Singleton: delete all other records before saving
        if not self.pk:
            HomepageAssemblySection.objects.all().delete()
        super().save(*args, **kwargs)

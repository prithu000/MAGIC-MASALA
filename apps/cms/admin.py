"""apps/cms/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from imagekit.admin import AdminThumbnail
from unfold.admin import ModelAdmin, TabularInline

from .models import AnnouncementBar, Banner, BlogPost, FAQItem, HeroSlide, HomepageAssemblySection, InfluencerReel, StaticPage, Testimonial


@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    list_display = ("title", "placement", "desktop_admin_thumbnail", "is_active", "display_order", "start_datetime", "end_datetime")
    list_editable = ("placement", "is_active", "display_order")
    list_filter = ("placement", "is_active")
    ordering = ["placement", "display_order"]

    desktop_admin_thumbnail = AdminThumbnail(image_field="desktop_image")
    desktop_admin_thumbnail.short_description = "Desktop Image"
    readonly_fields = ("desktop_admin_thumbnail",)

    fieldsets = (
        (
            "Banner Dimensions & Artwork",
            {
                "description": (
                    "<strong>📏 EXACT RECOMMENDED BANNER SIZES:</strong><br>"
                    "• <strong>Desktop Banner:</strong> <code>1920 × 500 px</code> (Aspect Ratio ~3.8:1 — Sleek & Compact)<br>"
                    "• <strong>Mobile Banner:</strong> <code>1080 × 600 px</code> (Aspect Ratio ~16:9 — Clean Phone View)<br>"
                    "<em>Tip: Text and promotional offers can be designed directly inside the image. The entire banner is clickable using the Link URL below.</em>"
                ),
                "fields": (
                    "placement",
                    "desktop_image",
                    "desktop_admin_thumbnail",
                    "mobile_image",
                    "cta_link",
                ),
            },
        ),
        (
            "Display Settings & Schedule",
            {
                "fields": (
                    "title",
                    "is_active",
                    "display_order",
                    "start_datetime",
                    "end_datetime",
                ),
            },
        ),
    )


@admin.register(AnnouncementBar)
class AnnouncementBarAdmin(ModelAdmin):
    list_display = ("message", "is_active", "display_order", "start_datetime", "end_datetime")
    list_editable = ("is_active", "display_order")


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ("placement", "admin_thumbnail", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    list_filter = ("placement",)

    admin_thumbnail = AdminThumbnail(image_field="image")
    readonly_fields = ("admin_thumbnail",)


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ("customer_name", "rating", "is_active", "display_order")
    list_editable = ("is_active", "display_order")


@admin.register(FAQItem)
class FAQItemAdmin(ModelAdmin):
    list_display = ("question", "is_active", "display_order")
    list_editable = ("is_active", "display_order")


@admin.register(StaticPage)
class StaticPageAdmin(ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "content")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )


@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    list_display = ("title", "published_at", "is_published")
    list_filter = ("published_at",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("admin_thumbnail",)

    admin_thumbnail = AdminThumbnail(image_field="featured_image")

    fieldsets = (
        (None, {"fields": ("title", "slug", "featured_image", "admin_thumbnail", "featured_image_alt", "content", "published_at")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )

    @admin.display(boolean=True, description="Published")
    def is_published(self, obj):
        return obj.is_published


from django.utils.html import format_html


@admin.register(InfluencerReel)
class InfluencerReelAdmin(ModelAdmin):
    list_display = ("influencer_name", "handle", "platform_badge", "reel_thumbnail", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    list_filter = ("platform", "is_active")
    search_fields = ("influencer_name", "handle", "caption")
    ordering = ["display_order"]

    reel_thumbnail = AdminThumbnail(image_field="thumbnail")
    reel_thumbnail.short_description = "Cover / Thumbnail"
    readonly_fields = ("reel_thumbnail", "embed_preview")

    fieldsets = (
        (
            "Creator Details",
            {"fields": ("influencer_name", "handle", "caption")},
        ),
        (
            "Direct Video Upload (Recommended for 100% Mobile Playback)",
            {
                "fields": ("video_file",),
                "description": (
                    "⭐ <strong>Direct MP4 Video:</strong> Upload an MP4 video file directly for crystal-clear, "
                    "instant native mobile video playback without any third-party ads, tracking, or iframe blocks."
                ),
            },
        ),
        (
            "Or Reel / Video Link (Instagram / YouTube)",
            {
                "fields": ("embed_url", "platform", "embed_preview"),
                "description": (
                    "💡 <strong>Easy Paste:</strong> Simply copy & paste ANY Instagram Reel link "
                    "(e.g. <code>https://www.instagram.com/reel/C8XYZ123/</code>) or YouTube Short/Video link "
                    "(e.g. <code>https://youtube.com/shorts/3-6LhXzJdQI</code>). "
                    "The system automatically detects whether it's Instagram or YouTube, extracts the reel ID, "
                    "and formats the embed for you upon saving."
                ),
            },
        ),
        (
            "Optional Cover Image",
            {
                "fields": ("thumbnail", "reel_thumbnail"),
                "description": "Recommended: 600×800 px portrait cover image shown before video begins.",
            },
        ),
        (
            "Visibility & Order",
            {"fields": ("is_active", "display_order")},
        ),
    )

    def platform_badge(self, obj):
        if obj.platform == "video" or obj.video_file:
            return mark_safe(
                '<span style="background:#059669;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">Direct Video</span>'
            )
        elif obj.platform == "instagram":
            return mark_safe(
                '<span style="background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);'
                'color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">Instagram</span>'
            )
        elif obj.platform == "youtube":
            return mark_safe(
                '<span style="background:#FF0000;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">YouTube</span>'
            )
        return format_html(
            '<span style="background:#6B7280;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{}</span>',
            obj.get_platform_display()
        )
    platform_badge.short_description = "Platform"

    def embed_preview(self, obj):
        if not obj.embed_url:
            return "No URL provided"
        if obj.platform == "instagram":
            return format_html(
                '<a href="{}" target="_blank" style="color:#E1306C;font-weight:600;">↗ Open Instagram Reel in new tab</a>',
                obj.embed_url
            )
        return format_html(
            '<a href="{}" target="_blank" style="color:#FF0000;font-weight:600;">↗ Preview YouTube Embed</a>',
            obj.embed_url
        )
    embed_preview.short_description = "Live Link"


@admin.register(HomepageAssemblySection)
class HomepageAssemblySectionAdmin(ModelAdmin):
    """
    Singleton admin — controls the hero image in the homepage scroll animation
    final reveal card.
    """
    list_display = ("__str__", "hero_image_preview", "is_active", "updated_at")
    list_editable = ("is_active",)
    readonly_fields = ("hero_image_preview", "updated_at")

    hero_image_preview = AdminThumbnail(image_field="hero_image")
    hero_image_preview.short_description = "Current Hero Image"

    fieldsets = (
        (
            "Assembly Section — Final Reveal Hero Image",
            {
                "description": (
                    "<strong>Homepage Scroll Assembly Section — Final Card Image</strong><br>"
                    "This image appears inside the dark premium card that slides in when the visitor "
                    "finishes scrolling through the 10-Spice assembly animation on the homepage.<br><br>"
                    "<strong>Recommended Image Size:</strong> <code>1200 × 675 px</code> (16:9 ratio, landscape)<br>"
                    "<strong>Format:</strong> JPG / WebP / PNG<br>"
                    "<strong>File Size:</strong> Keep under 2 MB for fast page load<br><br>"
                    "<em>Tip: Design the image to showcase all 10 spice jars together, or the combo pack box open "
                    "with jars inside. A premium product flat-lay photo works best.</em>"
                ),
                "fields": ("hero_image", "hero_image_preview", "is_active"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("updated_at",),
                "classes": ("collapse",),
            },
        ),
    )

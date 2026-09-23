"""apps/cms/views.py"""

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import BlogPost, FAQItem, HeroSlide, HomepageAssemblySection, InfluencerReel, StaticPage, Testimonial, Banner


def home(request):
    from apps.catalog.models import Category, Product
    from apps.combos.models import FixedCombo
    from apps.core.structured_data import organization_json_ld

    hero_slides = HeroSlide.objects.filter(is_active=True, placement=HeroSlide.Placement.HOMEPAGE).order_by("display_order")
    categories = Category.objects.filter(is_active=True).order_by("display_order")[:6]
    
    # Exactly 4 bestsellers for a balanced grid
    bestsellers = list(Product.objects.filter(is_active=True, is_bestseller=True)[:4])
    if len(bestsellers) < 4:
        extra_ids = [p.id for p in bestsellers]
        fillers = Product.objects.filter(is_active=True).exclude(id__in=extra_ids)[:4 - len(bestsellers)]
        bestsellers.extend(fillers)

    # Exactly 1 featured combo for homepage (admin selectable)
    featured_combo = FixedCombo.objects.filter(is_active=True, is_featured_on_homepage=True).first()
    if not featured_combo:
        featured_combo = FixedCombo.objects.filter(is_active=True).first()
    total_combos_count = FixedCombo.objects.filter(is_active=True).count()

    testimonials = Testimonial.objects.filter(is_active=True).order_by("display_order")[:6]
    from django.db.models import Q
    influencer_reels = (
        InfluencerReel.objects.filter(is_active=True)
        .filter(Q(embed_url__isnull=False) & ~Q(embed_url=""))
        .order_by("display_order")[:6]
    )
    banners = Banner.objects.filter(is_active=True, placement=Banner.Placement.HOMEPAGE).order_by("display_order")

    # Admin-editable assembly section hero image
    assembly_section = HomepageAssemblySection.objects.filter(is_active=True).first()

    return render(
        request,
        "cms/home.html",
        {
            "hero_slides": hero_slides,
            "categories": categories,
            "bestsellers": bestsellers,
            "featured_combo": featured_combo,
            "total_combos_count": total_combos_count,
            "testimonials": testimonials,
            "influencer_reels": influencer_reels,
            "banners": banners,
            "assembly_section": assembly_section,
            "organization_json_ld": organization_json_ld(request),
        },
    )


SLUG_ALIASES = {
    "about": "about-us",
    "shipping-policy": "shipping-returns",
    "refund-policy": "shipping-returns",
    "terms": "terms-of-service",
    "terms-of-use": "terms-of-service",
}


def static_page(request, slug):
    target_slug = SLUG_ALIASES.get(slug, slug)
    page = get_object_or_404(StaticPage, slug=target_slug)
    return render(
        request,
        "cms/static_page.html",
        {
            "page": page,
            "meta_title": page.meta_title or page.title,
            "meta_description": page.meta_description,
        },
    )


def blog_list(request):
    posts = BlogPost.objects.filter(
        published_at__isnull=False, published_at__lte=timezone.now()
    ).order_by("-published_at")
    return render(request, "cms/blog_list.html", {"posts": posts})


def blog_detail(request, slug):
    from apps.core.structured_data import breadcrumb_json_ld

    post = get_object_or_404(
        BlogPost, slug=slug, published_at__lte=timezone.now()
    )
    return render(
        request,
        "cms/blog_detail.html",
        {
            "post": post,
            "meta_title": post.meta_title or post.title,
            "meta_description": post.meta_description,
            "breadcrumb_json_ld": breadcrumb_json_ld(
                [("Home", "/"), ("Blog", "/blog/"), (post.title, post.get_absolute_url())],
                request,
            ),
        },
    )


def faq_view(request):
    from apps.core.structured_data import faq_json_ld

    items = FAQItem.objects.filter(is_active=True).order_by("display_order")
    return render(
        request,
        "cms/faq.html",
        {"items": items, "faq_json_ld": faq_json_ld(items)},
    )


def contact(request):
    return render(request, "cms/contact.html")

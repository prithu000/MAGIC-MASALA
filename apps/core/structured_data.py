"""
apps/core/structured_data.py
Helpers that return JSON-LD dicts for injection into <script type="application/ld+json"> tags.
"""

import json
from decimal import Decimal


def product_json_ld(product, request=None) -> str:
    """JSON-LD Product schema for a product detail page."""
    from apps.core.models import SiteSettings

    settings = SiteSettings.get_solo()
    base_url = request.build_absolute_uri("/").rstrip("/") if request else ""

    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.short_description or "",
        "sku": product.sku,
        "image": base_url + product.main_image.url if product.main_image else "",
        "brand": {
            "@type": "Brand",
            "name": settings.brand_name,
        },
        "offers": {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": str(product.price),
            "availability": (
                "https://schema.org/InStock"
                if product.stock_quantity > 0
                else "https://schema.org/OutOfStock"
            ),
            "url": base_url + product.get_absolute_url(),
        },
    }

    if product.average_rating and product.review_count > 0:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(product.average_rating),
            "reviewCount": product.review_count,
            "bestRating": "5",
            "worstRating": "1",
        }

    return json.dumps(data)


def organization_json_ld(request=None) -> str:
    """JSON-LD Organization schema (rendered on every page via base.html)."""
    from apps.core.models import SiteSettings

    settings = SiteSettings.get_solo()
    base_url = request.build_absolute_uri("/").rstrip("/") if request else ""

    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": settings.brand_name,
        "url": base_url,
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": settings.support_phone,
            "contactType": "customer service",
        },
        "sameAs": [
            url
            for url in [
                settings.instagram_url,
                settings.facebook_url,
                settings.youtube_url,
            ]
            if url
        ],
    }

    return json.dumps(data)


def breadcrumb_json_ld(crumbs: list[tuple[str, str]], request=None) -> str:
    """
    JSON-LD BreadcrumbList.
    crumbs: list of (name, url) tuples, e.g. [("Home", "/"), ("Masalas", "/shop/masalas/")]
    """
    base_url = request.build_absolute_uri("/").rstrip("/") if request else ""

    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": name,
            "item": base_url + url,
        }
        for i, (name, url) in enumerate(crumbs)
    ]

    return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})


def faq_json_ld(faq_items) -> str:
    """JSON-LD FAQPage schema."""
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item.question,
                "acceptedAnswer": {"@type": "Answer", "text": item.answer},
            }
            for item in faq_items
        ],
    }
    return json.dumps(data)

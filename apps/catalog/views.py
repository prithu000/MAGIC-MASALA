"""
apps/catalog/views.py
Product listing, category view, product detail, and search.
"""

from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

import json

from apps.core.models import SiteSettings
from apps.core.structured_data import breadcrumb_json_ld, product_json_ld

from .models import Category, Product, Tag


class ProductListView(ListView):
    """Shop all products — filterable, sortable."""

    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("tags", "variants")
        )

        # Filter by category slug
        cat_slug = self.kwargs.get("category_slug") or self.request.GET.get("category")
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)

        # Filter by tag
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)

        # Filter by price range (safe numeric conversion)
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        if min_price:
            try:
                qs = qs.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                qs = qs.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Sorting
        sort = self.request.GET.get("sort", "-created_at")
        sort_map = {
            "price_asc": "price",
            "price_desc": "-price",
            "rating": "-average_rating",
            "newest": "-created_at",
        }
        qs = qs.order_by(sort_map.get(sort, "-created_at"))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.filter(is_active=True)
        ctx["current_category"] = self.kwargs.get("category_slug")
        ctx["breadcrumb_json_ld"] = breadcrumb_json_ld(
            [("Home", "/"), ("Shop", "/shop/")], self.request
        )
        return ctx


class CategoryDetailView(ProductListView):
    """Category-scoped product listing."""

    template_name = "catalog/product_list.html"

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"], is_active=True)
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category"] = self.category
        ctx["breadcrumb_json_ld"] = breadcrumb_json_ld(
            [("Home", "/"), ("Shop", "/shop/"), (self.category.name, self.category.get_absolute_url())],
            self.request,
        )
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("gallery_images", "variants", "tags")
        )

    def get_context_data(self, **kwargs):
        from apps.reviews.models import ProductReview

        ctx = super().get_context_data(**kwargs)
        product = self.object

        # Reviews
        ctx["reviews"] = ProductReview.objects.filter(
            product=product, is_approved=True
        ).select_related("user").order_by("-created_at")

        # Related products (same category, not self)
        ctx["related_products"] = (
            Product.objects.filter(category=product.category, is_active=True)
            .exclude(pk=product.pk)[:6]
        )

        # Structured data
        ctx["product_json_ld"] = product_json_ld(product, self.request)
        ctx["breadcrumb_json_ld"] = breadcrumb_json_ld(
            [
                ("Home", "/"),
                ("Shop", "/shop/"),
                (product.category.name, product.category.get_absolute_url()),
                (product.name, product.get_absolute_url()),
            ],
            self.request,
        )

        # Variants serialized for instant reactive UI
        variants_data = []
        for v in product.variants.filter(is_active=True):
            variants_data.append({
                "id": v.pk,
                "size_label": v.size_label,
                "price": f"{v.price:.2f}",
                "mrp": f"{v.mrp:.2f}" if v.mrp else None,
                "discount_percent": v.discount_percent,
                "savings_amount": f"{v.savings_amount:.2f}",
                "is_in_stock": v.is_in_stock,
                "stock_quantity": v.stock_quantity,
            })
        ctx["variants_json"] = json.dumps(variants_data)

        # Base product fallback pricing data
        ctx["base_product_data"] = json.dumps({
            "id": "",
            "price": f"{product.price:.2f}",
            "mrp": f"{product.mrp:.2f}" if product.mrp else None,
            "discount_percent": product.discount_percent,
            "savings_amount": f"{product.savings_amount:.2f}",
            "is_in_stock": product.is_in_stock,
            "stock_quantity": product.stock_quantity,
        })

        # FAQs (from CMS)
        from apps.cms.models import FAQItem
        ctx["faqs"] = FAQItem.objects.filter(is_active=True).order_by("display_order")[:6]

        # Meta
        ctx["meta_title"] = product.meta_title or product.name
        ctx["meta_description"] = product.meta_description or product.short_description

        return ctx


from apps.core.security import ratelimit


@ratelimit(rate="60/m", key="ip")
def search_view(request):
    """Full-text search — robust multi-word query across name, description, ingredients, category, and SKU."""
    query = request.GET.get("q", "").strip()[:100]
    products = Product.objects.none()

    if query:
        words = query.split()[:6]
        q_filter = Q()
        for word in words:
            q_filter &= (
                Q(name__icontains=word)
                | Q(short_description__icontains=word)
                | Q(description__icontains=word)
                | Q(ingredients__icontains=word)
                | Q(category__name__icontains=word)
                | Q(sku__icontains=word)
            )
        products = Product.objects.filter(is_active=True).filter(q_filter).distinct().order_by("-is_bestseller", "name")
        
        # If strict AND didn't match, fallback to OR matching
        if not products.exists():
            or_filter = Q()
            for word in words:
                or_filter |= (
                    Q(name__icontains=word)
                    | Q(short_description__icontains=word)
                    | Q(category__name__icontains=word)
                )
            products = Product.objects.filter(is_active=True).filter(or_filter).distinct().order_by("-is_bestseller", "name")

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        from django.http import JsonResponse
        results = []
        for p in products[:12]:
            img_url = ""
            if p.main_image:
                img_url = p.main_image.url
            elif p.thumbnail:
                img_url = p.thumbnail.url
            
            # Get pack size / weight safely from variants
            variant = p.variants.first()
            weight_str = variant.size_label if variant else ""

            results.append({
                "id": p.pk,
                "name": p.name,
                "price": str(p.effective_price),
                "mrp": str(p.mrp) if p.mrp else "",
                "weight": weight_str,
                "category": p.category.name if p.category else "",
                "url": p.get_absolute_url(),
                "image": img_url,
            })
        return JsonResponse({"results": results, "query": query, "total": products.count()})

    return render(
        request,
        "catalog/search_results.html",
        {"products": products, "query": query},
    )

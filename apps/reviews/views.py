"""apps/reviews/views.py"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from django.core.exceptions import ValidationError
from apps.core.security import ratelimit
from apps.core.validators import validate_image_size, validate_image_type
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem
from .models import ProductReview


@login_required
@require_POST
@ratelimit(rate="5/m", key="user_or_ip")
def submit_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    # Verified purchase check
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__order_status=Order.OrderStatus.DELIVERED,
    ).exists()

    if not has_purchased:
        messages.error(request, "You can only review products you have purchased.")
        return redirect(product.get_absolute_url())

    try:
        rating = int(request.POST.get("rating", 0))
    except (ValueError, TypeError):
        messages.error(request, "Please select a valid rating between 1 and 5.")
        return redirect(product.get_absolute_url())

    if not (1 <= rating <= 5):
        messages.error(request, "Please select a rating between 1 and 5.")
        return redirect(product.get_absolute_url())

    image_file = request.FILES.get("image")
    if image_file:
        try:
            validate_image_size(image_file)
            validate_image_type(image_file)
        except ValidationError as ve:
            messages.error(request, str(ve.message if hasattr(ve, "message") else ve))
            return redirect(product.get_absolute_url())

    review, created = ProductReview.objects.get_or_create(
        product=product,
        user=request.user,
        defaults={
            "rating": rating,
            "title": request.POST.get("title", "")[:150],
            "comment": request.POST.get("comment", "")[:2000],
            "image": image_file,
            "is_approved": False,
        },
    )

    if created:
        messages.success(request, "Thank you — your review is pending approval.")
    else:
        messages.info(request, "You have already submitted a review for this product.")

    return redirect(product.get_absolute_url())

"""apps/reviews/admin.py"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ProductReview


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = ("product", "user", "rating", "title", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")
    list_editable = ("is_approved",)
    search_fields = ("product__name", "user__email", "title", "comment")
    readonly_fields = ("product", "user", "rating", "title", "comment", "image", "created_at")
    actions = ["approve_reviews", "reject_reviews"]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ("created_at",)
        return self.readonly_fields

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        for review in queryset:
            review.is_approved = True
            review.save()

    @admin.action(description="Reject (unapprove) selected reviews")
    def reject_reviews(self, request, queryset):
        for review in queryset:
            review.is_approved = False
            review.save()

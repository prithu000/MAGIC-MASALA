"""apps/payments/admin.py"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = ("order", "gateway", "gateway_payment_id", "amount", "status", "created_at")
    list_filter = ("status", "gateway")
    readonly_fields = [f.name for f in PaymentTransaction._meta.fields]
    search_fields = ("order__order_number", "gateway_order_id", "gateway_payment_id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

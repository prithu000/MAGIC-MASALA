"""
apps/orders/models.py
Order, OrderItem, OrderStatusHistory
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


def generate_order_number():
    year = timezone.now().year
    uid = uuid.uuid4().hex[:6].upper()
    return f"MU-{year}-{uid}"


class Order(models.Model):
    class PaymentMethod(models.TextChoices):
        ONLINE = "online", "Online Payment"
        COD = "cod", "Cash on Delivery"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ADVANCE_PAID = "advance_paid", "Advance Paid (COD)"
        FULLY_PAID = "paid", "Fully Paid"
        COD_COLLECTED = "cod_collected", "COD Collected"
        FAILED = "failed", "Payment Failed"
        REFUNDED = "refunded", "Refunded"

    class OrderStatus(models.TextChoices):
        PLACED = "placed", "Placed"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        RETURNED = "returned", "Returned"

    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")

    # Address snapshot — captured at order time so later edits don't rewrite history
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=15)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_landmark = models.CharField(max_length=150, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)

    # Financials
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    cod_charge_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)

    # Coupon reference (for display; actual discount_amount is snapshotted above)
    coupon = models.ForeignKey("coupons.Coupon", on_delete=models.SET_NULL, null=True, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)

    # Tax Invoice & GST Compliance (Mahila Udhyog Bill Book)
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Official sequential Tax Invoice number (e.g. MU/26-27/0081).",
    )
    invoice_date = models.DateField(
        null=True,
        blank=True,
        help_text="Official invoice date printed on bill.",
    )
    customer_gstin = models.CharField(
        max_length=20,
        blank=True,
        help_text="Purchaser GSTIN (if registered dealer/firm).",
    )
    transport_mode = models.CharField(
        max_length=50,
        blank=True,
        default="Road",
        help_text="Mode of transport (e.g. Road, Courier, Tempo).",
    )
    vehicle_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Vehicle Reg No or LR Tracking No.",
    )
    place_of_supply = models.CharField(
        max_length=100,
        blank=True,
        help_text="State / jurisdiction of supply (e.g. Uttar Pradesh (09)).",
    )
    is_interstate = models.BooleanField(
        default=False,
        help_text="True if delivery is outside UP (IGST applicable), False for intra-UP (CGST+SGST).",
    )
    taxable_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True,
        help_text="Total value before taxes.",
    )
    cgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True,
        help_text="Central GST (2.5% for 5% goods within UP).",
    )
    sgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True,
        help_text="State GST (2.5% for 5% goods within UP).",
    )
    igst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True,
        help_text="Integrated GST (5.0% for interstate supply).",
    )

    # Payment
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # COD specifics
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True)

    # Order status
    order_status = models.CharField(max_length=15, choices=OrderStatus.choices, default=OrderStatus.PLACED)

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    courier_name = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def snapshot_address(self, address):
        """Copy an Address instance into the order's shipping fields."""
        self.shipping_full_name = address.full_name
        self.shipping_phone = address.phone
        self.shipping_address_line1 = address.address_line1
        self.shipping_address_line2 = address.address_line2
        self.shipping_landmark = address.landmark
        self.shipping_city = address.city
        self.shipping_state = address.state
        self.shipping_pincode = address.pincode

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_status = Order.objects.filter(pk=self.pk).values_list("order_status", flat=True).first()
            except Exception:
                pass

        super().save(*args, **kwargs)

        # Auto create history entry on status change or creation
        if is_new:
            OrderStatusHistory.objects.get_or_create(
                order=self,
                status=self.order_status,
                defaults={"note": "Order placed by customer."}
            )
        elif old_status and old_status != self.order_status:
            note = f"Order status updated to {self.get_order_status_display()}."
            if self.order_status == self.OrderStatus.SHIPPED:
                details = []
                if self.courier_name:
                    details.append(f"Courier: {self.courier_name}")
                if self.tracking_number:
                    details.append(f"Tracking #{self.tracking_number}")
                if details:
                    note += f" ({', '.join(details)})"
            elif self.order_status == self.OrderStatus.DELIVERED:
                note = "Order has been successfully delivered."
            elif self.order_status == self.OrderStatus.CANCELLED:
                note = "Order has been cancelled."
            elif self.order_status == self.OrderStatus.PACKED:
                note = "Your spices are packed and ready for dispatch."

            OrderStatusHistory.objects.create(
                order=self,
                status=self.order_status,
                note=note
            )

            # Dispatch branded delivery & tracking email update to customer
            try:
                from apps.core.email_service import send_order_status_update_email
                send_order_status_update_email(self, self.get_order_status_display(), self.order_status)
            except Exception:
                pass

    def add_status(self, status: str, note: str = ""):
        self.order_status = status
        self.save(update_fields=["order_status", "updated_at"])
        if note:
            OrderStatusHistory.objects.filter(order=self, status=status).update(note=note)

    @property
    def is_cancellable(self) -> bool:
        return self.order_status in (self.OrderStatus.PLACED, self.OrderStatus.CONFIRMED)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.SET_NULL, null=True, blank=True
    )
    fixed_combo = models.ForeignKey(
        "combos.FixedCombo", on_delete=models.SET_NULL, null=True, blank=True
    )
    item_name = models.CharField(max_length=255, blank=True)  # Snapshotted name
    quantity = models.PositiveSmallIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Snapshotted price

    # GST / Tax invoice item breakdown
    hsn_code = models.CharField(max_length=8, blank=True, default="0910", help_text="4-digit HSN code")
    gst_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("5.00"), help_text="Applicable GST rate (%)"
    )
    taxable_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True, help_text="Taxable amount for this line"
    )
    cgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True
    )
    sgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True
    )
    igst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), blank=True
    )

    def __str__(self):
        return f"{self.quantity}× {self.item_name}"

    def save(self, *args, **kwargs):
        if self.product:
            if not self.item_name:
                self.item_name = self.product.name
            if self.price_at_purchase is None:
                self.price_at_purchase = self.product.price
            if not self.hsn_code and self.product.hsn_code:
                self.hsn_code = self.product.hsn_code
            if (self.gst_rate is None or self.gst_rate == Decimal("5.00")) and self.product.gst_rate:
                self.gst_rate = self.product.gst_rate
        elif self.fixed_combo:
            if not self.item_name:
                self.item_name = self.fixed_combo.name
            if self.price_at_purchase is None:
                self.price_at_purchase = self.fixed_combo.combo_price
            if not self.hsn_code:
                self.hsn_code = "0910"
        if self.price_at_purchase is None:
            self.price_at_purchase = Decimal("0.00")
        super().save(*args, **kwargs)

    @property
    def line_total(self):
        if self.price_at_purchase is not None and self.quantity is not None:
            return self.price_at_purchase * self.quantity
        return Decimal("0.00")


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=15, choices=Order.OrderStatus.choices)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.order.order_number} — {self.get_status_display()} at {self.timestamp}"

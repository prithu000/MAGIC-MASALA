"""
apps/core/tests.py — Automated security audit verification suite.
"""

from decimal import Decimal
import hmac
import hashlib
import json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentTransaction
from apps.coupons.models import Coupon
from apps.accounts.models import Address

User = get_user_model()


class SecurityAuditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(
            username="usera", email="usera@example.com", password="Password123!"
        )
        self.user_b = User.objects.create_user(
            username="userb", email="userb@example.com", password="Password123!"
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Turmeric Powder",
            slug="turmeric-powder",
            price=Decimal("150.00"),
            mrp=Decimal("180.00"),
            is_active=True,
        )
        self.order_a = Order.objects.create(
            user=self.user_a,
            order_number="MM-TEST-001",
            total=Decimal("300.00"),
            payment_method=Order.PaymentMethod.ONLINE,
        )

    def test_payment_checkout_idor_protection(self):
        """User B cannot access or initiate payment for User A's order."""
        self.client.force_login(self.user_b)
        response = self.client.get(reverse("payments:razorpay_checkout", args=[self.order_a.pk]))
        # Must be redirected away
        self.assertRedirects(response, reverse("cart:detail"))

    def test_payment_checkout_unauthenticated_idor_protection(self):
        """Unauthenticated attacker cannot access User A's payment checkout."""
        response = self.client.get(reverse("payments:razorpay_checkout", args=[self.order_a.pk]))
        self.assertRedirects(response, reverse("cart:detail"))

    def test_webhook_invalid_signature_rejected(self):
        """Tampered or invalid signature on webhook returns 400 Bad Request."""
        payload = json.dumps({"event": "payment.captured", "payload": {}})
        response = self.client.post(
            reverse("payments:razorpay_webhook"),
            data=payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="forged_signature_hex",
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_idempotency(self):
        """Webhooks processing is idempotent; duplicate capture events do not corrupt state."""
        from apps.payments.views import _handle_payment_captured

        txn = PaymentTransaction.objects.create(
            order=self.order_a,
            gateway="razorpay",
            gateway_order_id="order_test_123",
            amount=Decimal("300.00"),
            status=PaymentTransaction.Status.CREATED,
            raw_response={},
        )
        fake_entity = {
            "order_id": "order_test_123",
            "id": "pay_test_456",
            "amount": 30000,
            "currency": "INR",
        }

        # First webhook execution
        _handle_payment_captured(fake_entity)
        txn.refresh_from_db()
        self.assertEqual(txn.status, PaymentTransaction.Status.CAPTURED)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.payment_status, Order.PaymentStatus.FULLY_PAID)

        # Second webhook execution (duplicate replay)
        _handle_payment_captured(fake_entity)
        txn.refresh_from_db()
        self.assertEqual(txn.status, PaymentTransaction.Status.CAPTURED)

    def test_cart_quantity_clamping(self):
        """CartService prevents negative or excessive quantities."""
        from apps.cart.services import CartService
        from django.test.client import RequestFactory

        rf = RequestFactory()
        req = rf.get("/")
        req.user = self.user_a
        req.session = self.client.session

        # Negative quantity clamped to 1
        item = CartService.add_item(req, product_id=self.product.pk, quantity=-5)
        self.assertEqual(item.quantity, 1)

        # Huge quantity clamped to 50
        item_updated = CartService.update_item(req, item.pk, quantity=999999)
        self.assertEqual(item_updated.quantity, 50)

    def test_coupon_guest_abuse_prevention(self):
        """Guest users cannot apply first-order-only or per-customer restricted coupons."""
        from apps.coupons.services import CouponService, CouponError
        from django.test.client import RequestFactory
        from apps.cart.services import CartService

        coupon = Coupon.objects.create(
            code="FIRSTORDER",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            first_order_only=True,
            is_active=True,
        )

        rf = RequestFactory()
        req = rf.get("/")
        from django.contrib.auth.models import AnonymousUser
        req.user = AnonymousUser()
        req.session = self.client.session
        cart = CartService.get_or_create_cart(req)

        with self.assertRaises(CouponError) as cm:
            CouponService.validate("FIRSTORDER", req.user, cart)
        self.assertIn("log in", str(cm.exception).lower())

    def test_address_state_modification_requires_post(self):
        """address_set_default and address_delete reject GET requests."""
        addr = Address.objects.create(
            user=self.user_a,
            full_name="User A",
            phone="9876543210",
            address_line1="123 Test Street",
            city="Kasganj",
            state="Uttar Pradesh",
            pincode="207123",
            is_default=False,
        )
        self.client.force_login(self.user_a)

        # GET request to set-default must fail with 405 Method Not Allowed
        response_get = self.client.get(reverse("accounts:address_set_default", args=[addr.pk]))
        self.assertEqual(response_get.status_code, 405)

        # POST request works
        response_post = self.client.post(reverse("accounts:address_set_default", args=[addr.pk]))
        self.assertRedirects(response_post, reverse("accounts:address_list"))
        addr.refresh_from_db()
        self.assertTrue(addr.is_default)

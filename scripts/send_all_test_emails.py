"""
scripts/send_all_test_emails.py
Utility script to test and dispatch all 6 customer email templates to a specified email address.
Usage:
    .\\venv\\Scripts\\python.exe scripts/send_all_test_emails.py [recipient@example.com]
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

import time

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.core.models import EmailSettings, EmailCampaign, EmailLog
from apps.core.email_service import (
    send_welcome_email,
    send_order_confirmation_email,
    send_order_status_update_email,
    send_password_reset_email,
    send_password_changed_email,
    broadcast_campaign,
    send_templated_email,
)
from apps.orders.models import Order, OrderItem

User = get_user_model()


def send_all_test_emails(target_email="prithumaheshwari@gmail.com"):
    print("=" * 70)
    print(f"🚀 DISPATCHING COMPLETE SUITE OF EMAILS TO: {target_email}")
    print("=" * 70)

    # 1. Ensure user exists
    user, _ = User.objects.get_or_create(
        email=target_email,
        defaults={
            "username": target_email.split("@")[0],
            "first_name": "Prithu",
            "last_name": "Maheshwari",
        },
    )

    # 2. Ensure test order exists
    order, _ = Order.objects.get_or_create(
        order_number="MM-2026-TEST",
        defaults={
            "user": user,
            "shipping_full_name": "Prithu Maheshwari",
            "shipping_phone": "7805105024",
            "shipping_address_line1": "Flat 402, Royal Residency",
            "shipping_address_line2": "Civil Lines",
            "shipping_city": "Kasganj",
            "shipping_state": "Uttar Pradesh",
            "shipping_pincode": "207123",
            "subtotal": Decimal("999.00"),
            "discount_amount": Decimal("100.00"),
            "tax_amount": Decimal("45.00"),
            "shipping_charge": Decimal("0.00"),
            "total": Decimal("944.00"),
            "payment_method": Order.PaymentMethod.ONLINE,
            "payment_status": Order.PaymentStatus.FULLY_PAID,
            "order_status": Order.OrderStatus.SHIPPED,
            "invoice_number": "MM/26-27/0001",
        },
    )

    if not order.items.exists():
        OrderItem.objects.create(
            order=order,
            item_name="Kashmiri Lal Mirch (Cold Stone Ground) - 200g",
            quantity=2,
            price_at_purchase=Decimal("249.00"),
            taxable_value=Decimal("474.28"),
            gst_rate=Decimal("5.00"),
            cgst_amount=Decimal("11.86"),
            sgst_amount=Decimal("11.86"),
        )
        OrderItem.objects.create(
            order=order,
            item_name="Custom 10-Spice Kitchen Combo Box",
            quantity=1,
            price_at_purchase=Decimal("499.00"),
            taxable_value=Decimal("475.24"),
            gst_rate=Decimal("5.00"),
            cgst_amount=Decimal("11.88"),
            sgst_amount=Decimal("11.88"),
        )

    # Ensure sample campaign exists
    campaign, _ = EmailCampaign.objects.get_or_create(
        title="Festive Mega Spice Combo Offer — 20% OFF",
        defaults={
            "subject": "🌶️ Special Spice Offer: 20% OFF on Custom Spice Combos!",
            "preview_text": "Pure stone-ground spices for your kitchen. Use code FESTIVE20 for 20% off!",
            "badge_text": "LIMITED TIME FESTIVE OFFER",
            "heading": "Pure, Stone-Ground Spices for Festive Flavours",
            "subheading": "Handcrafted with love at our traditional Kasganj mill with zero preservatives.",
            "message_body": "Celebrate this festive season with authentic home-cooked meals. Enjoy an exclusive flat 20% discount across our entire range of stone-ground single spices and custom combo boxes. Crafted fresh upon order!",
            "coupon_code": "FESTIVE20",
            "discount_highlight": "FLAT 20% OFF",
            "cta_text": "Claim 20% Off & Shop Now →",
            "cta_url": "/combos/",
            "status": "draft",
        },
    )

    tests = [
        ("1. Welcome Email (with WELCOME10 coupon)", lambda: send_welcome_email(user)),
        ("2. Order Confirmation Email (Itemized receipt)", lambda: send_order_confirmation_email(order)),
        ("3. Order Status & Delivery Update (Shipped)", lambda: send_order_status_update_email(order, "Shipped with BlueDart (AWB: BLUEDART987654321)", "shipped")),
        ("4. Password Reset Link", lambda: send_password_reset_email(user, "https://mumagicmasala.com/account/password-reset/confirm/MQ/test-token/")),
        ("5. Password Changed Security Alert", lambda: send_password_changed_email(user)),
        ("6. Promotional Offer Campaign (FESTIVE20)", lambda: broadcast_campaign(campaign, test_email=target_email)),
    ]

    for name, func in tests:
        print(f"\n📨 Sending {name}...")
        try:
            func()
            print(f"   ↳ Dispatched call completed.")
        except Exception as e:
            print(f"   ↳ Error: {e}")

    print("\nWaiting 8 seconds for all 6 Brevo SMTP delivery threads to finish...")
    time.sleep(8)

    print("\n" + "=" * 70)
    print("DISPATCH COMPLETED. Checking latest logs from EmailLog table...")
    print("=" * 70)

    logs = EmailLog.objects.filter(recipient=target_email).order_by("-created_at")[:6]
    for log in logs:
        status_icon = "✅" if log.status == EmailLog.Status.SENT else "❌"
        print(f"{status_icon} [{log.email_type.upper()}] Status: {log.status.upper()} | Subject: {log.subject}")
        if log.error_message:
            print(f"   ⚠️ Error Details: {log.error_message}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "prithumaheshwari@gmail.com"
    send_all_test_emails(target)

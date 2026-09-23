"""
apps/payments/views.py — Razorpay payment flow.

Flow:
1. /payments/checkout/<order_id>/ → creates Razorpay order → renders checkout page with JS modal
2. Customer pays via Razorpay modal (UPI, card, netbanking, wallet)
3. Razorpay fires webhook to /payments/webhook/razorpay/
4. Webhook verifies HMAC signature → marks order paid → fires confirmation email
5. Client redirect goes to /checkout/confirm/<order_number>/ (display only — no payment logic)
"""

import hashlib
import hmac
import json
import logging

import razorpay
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.orders.models import Order
from apps.orders.tasks import send_order_confirmation_email

from .models import PaymentTransaction

from apps.core.security import ratelimit

logger = logging.getLogger(__name__)


def _razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def razorpay_checkout(request, order_id):
    """Create a Razorpay order and render the payment page with strict ownership verification."""
    order = get_object_or_404(Order, pk=order_id)

    # Strict authorization check to prevent IDOR
    is_owner = False
    if request.user.is_authenticated and order.user_id == request.user.id:
        is_owner = True
    elif request.session.get("pending_order_id") == order.pk or request.session.get("confirmed_order") == order.pk:
        is_owner = True

    if not is_owner:
        logger.warning(
            "Unauthorized access attempt to payment checkout for order %s from IP %s",
            order.pk,
            request.META.get("REMOTE_ADDR"),
        )
        messages.error(request, "You do not have permission to access this payment checkout.")
        return redirect("cart:detail")

    # For COD orders (testing mode without online advance), redirect straight to confirmation
    if order.payment_method == Order.PaymentMethod.COD:
        request.session["confirmed_order"] = order.pk
        return redirect("orders:order_confirmation", order_number=order.order_number)

    # Determine amount to collect now
    amount_to_collect = order.total

    # Amount in paise (Razorpay uses smallest currency unit)
    amount_paise = int(amount_to_collect * 100)

    # Check if Razorpay keys are configured at all
    razorpay_key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    razorpay_key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not razorpay_key_id or not razorpay_key_secret or razorpay_key_id.startswith("rzp_test_xxx"):
        if settings.DEBUG and getattr(settings, "ALLOW_DEV_PAYMENT_SIMULATION", False):
            request.session["confirmed_order"] = order.pk
            messages.success(
                request,
                f"🧪 Dev Mode: Order #{order.order_number} placed successfully! "
                "(Payment gateway simulated — add Razorpay test keys to process real payments.)"
            )
            return redirect("orders:order_confirmation", order_number=order.order_number)
        messages.error(request, "Payment gateway is not configured. Please contact support.")
        return redirect("orders:checkout_payment")

    try:
        client = _razorpay_client()
        rzp_order = client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": order.order_number,
                "notes": {"order_id": str(order.pk)},
            }
        )
    except Exception as e:
        logger.warning("Razorpay order creation failed: %s", e)
        # Never simulate in production. Only allow in local dev if explicitly configured.
        if settings.DEBUG and getattr(settings, "ALLOW_DEV_PAYMENT_SIMULATION", False):
            request.session["confirmed_order"] = order.pk
            messages.info(request, f"Testing Mode: Order #{order.order_number} confirmed (Online gateway simulated).")
            return redirect("orders:order_confirmation", order_number=order.order_number)
        messages.error(request, "Payment gateway is currently unavailable. Please try again or select COD.")
        return redirect("orders:checkout_payment")

    # Record the transaction
    txn = PaymentTransaction.objects.create(
        order=order,
        gateway="razorpay",
        gateway_order_id=rzp_order["id"],
        amount=amount_to_collect,
        status=PaymentTransaction.Status.CREATED,
        raw_response=rzp_order,
    )

    return render(
        request,
        "payments/razorpay_checkout.html",
        {
            "order": order,
            "razorpay_key_id": razorpay_key_id,
            "razorpay_order_id": rzp_order["id"],
            "amount_paise": amount_paise,
            "amount_display": amount_to_collect,
            "is_cod_advance": order.payment_method == Order.PaymentMethod.COD,
        },
    )



@csrf_exempt
@require_POST
@ratelimit(rate="120/m", key="ip")
def razorpay_webhook(request):
    """
    Razorpay webhook handler.
    Verifies HMAC-SHA256 signature before trusting any payment confirmation.
    Never trust the client-side redirect alone.
    """
    payload = request.body
    if len(payload) > 65536:
        return HttpResponseBadRequest("Payload too large")

    received_signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify signature
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        logger.warning("Razorpay webhook: invalid signature")
        return HttpResponseBadRequest("Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    event_type = event.get("event")
    logger.info("Razorpay webhook event: %s", event_type)

    if event_type == "payment.captured":
        payment_entity = event["payload"]["payment"]["entity"]
        _handle_payment_captured(payment_entity)

    elif event_type == "payment.failed":
        payment_entity = event["payload"]["payment"]["entity"]
        _handle_payment_failed(payment_entity)

    return HttpResponse(status=200)


def _handle_payment_captured(payment_entity: dict):
    """Mark the order as paid and send confirmation email with atomic idempotency."""
    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")

    with transaction.atomic():
        try:
            txn = PaymentTransaction.objects.select_for_update().select_related("order").get(
                gateway_order_id=razorpay_order_id
            )
        except PaymentTransaction.DoesNotExist:
            logger.error("No transaction for Razorpay order_id=%s", razorpay_order_id)
            return

        # Idempotency check: if already CAPTURED, skip re-processing
        if txn.status == PaymentTransaction.Status.CAPTURED:
            logger.info("Webhook duplicate: transaction %s is already CAPTURED", razorpay_order_id)
            return

        # Security check: verify payment amount and currency match expected values exactly
        paid_amount_paise = payment_entity.get("amount")
        paid_currency = payment_entity.get("currency")
        expected_amount_paise = int(txn.amount * 100)

        if paid_currency != "INR" or paid_amount_paise != expected_amount_paise:
            logger.critical(
                "PAYMENT FRAUD ALERT: Razorpay amount/currency mismatch! Expected %s paise INR, received %s paise %s for order %s (txn %s)",
                expected_amount_paise,
                paid_amount_paise,
                paid_currency,
                txn.order.order_number,
                txn.pk,
            )
            txn.status = PaymentTransaction.Status.FAILED
            txn.raw_response = {
                **txn.raw_response,
                "payment": payment_entity,
                "security_error": f"Amount/currency mismatch. Expected {expected_amount_paise} paise INR, got {paid_amount_paise} paise {paid_currency}",
            }
            txn.save()
            return

        txn.gateway_payment_id = razorpay_payment_id
        txn.status = PaymentTransaction.Status.CAPTURED
        txn.raw_response = {**txn.raw_response, "payment": payment_entity}
        txn.save()

        order = txn.order
        if order.payment_method == Order.PaymentMethod.COD:
            order.payment_status = Order.PaymentStatus.ADVANCE_PAID
        else:
            order.payment_status = Order.PaymentStatus.FULLY_PAID

        order.add_status(Order.OrderStatus.CONFIRMED, "Payment confirmed by gateway.")
        order.save()

    try:
        send_order_confirmation_email.delay(order.pk)
    except Exception:
        try:
            from apps.core.email_service import send_order_confirmation_email as deliver_order_confirmation
            deliver_order_confirmation(order)
        except Exception as email_err:
            logger.error("Failed to dispatch order confirmation email: %s", email_err)
    logger.info("Payment captured for order %s", order.order_number)


def _handle_payment_failed(payment_entity: dict):
    razorpay_order_id = payment_entity.get("order_id")
    with transaction.atomic():
        try:
            txn = PaymentTransaction.objects.select_for_update().select_related("order").get(
                gateway_order_id=razorpay_order_id
            )
            txn.status = PaymentTransaction.Status.FAILED
            txn.raw_response = {**txn.raw_response, "payment": payment_entity}
            txn.save()
            order = txn.order
            order.payment_status = Order.PaymentStatus.FAILED
            order.save(update_fields=["payment_status"])
            logger.warning("Payment failed for order %s", order.order_number)
        except PaymentTransaction.DoesNotExist:
            logger.error("No transaction for failed Razorpay order_id=%s", razorpay_order_id)


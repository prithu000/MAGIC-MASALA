"""
apps/core/email_service.py — Professional Email Notification & Campaign System for Magic Masala.
Handles Brevo SMTP delivery, template rendering, logging, and asynchronous dispatch.
"""

import logging
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def get_email_settings():
    """Fetch active EmailSettings from DB singleton, with safe fallback."""
    try:
        from apps.core.models import EmailSettings
        return EmailSettings.get_solo()
    except Exception:
        return None


def get_configured_connection(email_settings=None):
    """
    Returns a configured SMTP connection using Brevo credentials.
    Prefers EmailSettings admin values if populated, otherwise defaults to django settings.
    """
    if not email_settings:
        email_settings = get_email_settings()

    if email_settings and email_settings.smtp_host and email_settings.smtp_password:
        return get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=email_settings.smtp_host,
            port=email_settings.smtp_port,
            username=email_settings.smtp_user,
            password=email_settings.smtp_password,
            use_tls=email_settings.smtp_use_tls,
            fail_silently=False,
        )
    return get_connection(fail_silently=False)


def _deliver_email(subject: str, html_message: str, plain_message: str, from_email: str,
                   recipient_list: list, email_type: str, email_settings=None):
    """Internal delivery and logging worker function."""
    from apps.core.models import EmailLog

    connection = None
    try:
        connection = get_configured_connection(email_settings)
    except Exception as exc:
        logger.error("Failed to initialize Brevo email connection: %s", exc)

    for recipient in recipient_list:
        if not recipient or "@" not in recipient:
            continue

        status = EmailLog.Status.SENT
        error_msg = ""

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[recipient],
                connection=connection,
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            logger.info("Email [%s] sent successfully to %s: %s", email_type, recipient, subject)
        except Exception as exc:
            status = EmailLog.Status.FAILED
            error_msg = str(exc)
            logger.error("Failed to deliver [%s] email to %s: %s", email_type, recipient, exc)

        # Record in EmailLog for audit & tracking in Admin
        try:
            EmailLog.objects.create(
                email_type=email_type,
                recipient=recipient,
                subject=subject,
                status=status,
                error_message=error_msg[:1000] if error_msg else "",
            )
        except Exception:
            pass


def send_templated_email(subject: str, template_name: str, context: dict, recipient_list: list,
                         email_type: str = "other", async_send: bool = True):
    """
    Renders HTML email template and dispatches to recipient list.
    Runs asynchronously in a background thread by default so user requests never lag.
    """
    email_settings = get_email_settings()
    if email_settings and not email_settings.is_enabled:
        logger.info("Outgoing emails are globally disabled in EmailSettings.")
        return

    from_name = email_settings.from_name if email_settings else "MU Magic Masala"
    from_addr = email_settings.from_email if email_settings else getattr(settings, "DEFAULT_FROM_EMAIL", "care@mumagicmasala.com")
    from_email = f"{from_name} <{from_addr}>" if "<" not in from_addr else from_addr

    # Add global settings context
    context.update({
        "email_settings": email_settings,
        "site_url": "https://mumagicmasala.com",
    })

    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
    except Exception as exc:
        logger.error("Failed to render email template %s: %s", template_name, exc)
        return

    if async_send:
        t = threading.Thread(
            target=_deliver_email,
            args=(subject, html_message, plain_message, from_email, recipient_list, email_type, email_settings),
            daemon=True,
        )
        t.start()
    else:
        _deliver_email(subject, html_message, plain_message, from_email, recipient_list, email_type, email_settings)


# -----------------------------------------------------------------------------
# High-Level Email Notification APIs
# -----------------------------------------------------------------------------

def send_welcome_email(user):
    """Sends warm welcome email with coupon when customer registers."""
    if not user.email:
        return

    email_settings = get_email_settings()
    if email_settings and not email_settings.welcome_email_enabled:
        return

    subject = email_settings.welcome_email_subject if email_settings else "Welcome to MU Magic Masala! 🌶️"
    coupon_code = email_settings.welcome_coupon_code if email_settings else "WELCOME10"

    send_templated_email(
        subject=subject,
        template_name="emails/welcome.html",
        context={
            "user": user,
            "coupon_code": coupon_code,
            "preview_text": "Welcome to fresh, stone-ground authentic spices. Enjoy 10% off your first box!",
        },
        recipient_list=[user.email],
        email_type="welcome",
        async_send=True,
    )


def send_order_confirmation_email(order):
    """Sends detailed order receipt and bill summary when an order is confirmed."""
    email_settings = get_email_settings()
    if email_settings and not email_settings.order_confirmation_enabled:
        return

    recipient = None
    if order.user and order.user.email:
        recipient = order.user.email
    elif hasattr(order, "shipping_email") and order.shipping_email:
        recipient = order.shipping_email

    if not recipient:
        return

    template_subject = email_settings.order_confirmation_subject if email_settings else "Order Confirmed — #{order_number} | MU Magic Masala"
    subject = template_subject.replace("{order_number}", str(order.order_number))

    send_templated_email(
        subject=subject,
        template_name="emails/order_confirmation.html",
        context={
            "order": order,
            "preview_text": f"Your order #{order.order_number} is confirmed! Total: ₹{order.total}",
        },
        recipient_list=[recipient],
        email_type="order_confirmation",
        async_send=True,
    )


def send_order_status_update_email(order, status_display: str, status_code: str = ""):
    """Sends tracking & delivery update email when order status changes."""
    email_settings = get_email_settings()
    if email_settings and not email_settings.order_status_update_enabled:
        return

    recipient = None
    if order.user and order.user.email:
        recipient = order.user.email
    elif hasattr(order, "shipping_email") and order.shipping_email:
        recipient = order.shipping_email

    if not recipient:
        return

    template_subject = email_settings.order_status_subject if email_settings else "Order Update: #{order_number} is now {status_display} | MU Magic Masala"
    subject = template_subject.replace("{order_number}", str(order.order_number)).replace("{status_display}", str(status_display))

    send_templated_email(
        subject=subject,
        template_name="emails/order_status_update.html",
        context={
            "order": order,
            "status_display": status_display,
            "status_code": status_code or order.order_status,
            "preview_text": f"Update on Order #{order.order_number}: {status_display}",
        },
        recipient_list=[recipient],
        email_type="status_update",
        async_send=True,
    )


def send_password_reset_email(user, reset_url: str):
    """Sends secure password reset link."""
    if not user.email:
        return

    send_templated_email(
        subject="Reset Your MU Magic Masala Password",
        template_name="emails/password_reset.html",
        context={
            "user": user,
            "reset_url": reset_url,
            "preview_text": "Follow this link to securely reset your password.",
        },
        recipient_list=[user.email],
        email_type="password_reset",
        async_send=True,
    )


def send_password_changed_email(user):
    """Sends security confirmation email when password is changed."""
    if not user.email:
        return

    email_settings = get_email_settings()
    if email_settings and not email_settings.password_change_enabled:
        return

    subject = email_settings.password_change_subject if email_settings else "Security Alert: Your Password Was Changed"

    send_templated_email(
        subject=subject,
        template_name="emails/password_changed.html",
        context={
            "user": user,
            "timestamp": timezone.now().strftime("%d %b %Y, %I:%M %p"),
            "preview_text": "Your account password was recently modified.",
        },
        recipient_list=[user.email],
        email_type="password_change",
        async_send=True,
    )


def broadcast_campaign(campaign, test_email: str = None) -> int:
    """
    Sends an offer or marketing campaign.
    If `test_email` is passed, delivers to that test address only.
    Otherwise broadcasts to all registered customer email addresses.
    Returns the count of recipients queued.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if test_email:
        recipients = [test_email.strip()]
    else:
        # All users with valid emails
        recipients = list(User.objects.filter(is_active=True).exclude(email="").values_list("email", flat=True).distinct())

    cta_full_url = campaign.cta_url
    if cta_full_url.startswith("/"):
        cta_full_url = f"https://mumagicmasala.com{cta_full_url}"

    for email in recipients:
        send_templated_email(
            subject=campaign.subject,
            template_name="emails/promotional_campaign.html",
            context={
                "campaign": campaign,
                "cta_full_url": cta_full_url,
                "preview_text": campaign.preview_text or campaign.heading,
            },
            recipient_list=[email],
            email_type="campaign",
            async_send=True,
        )

    if not test_email:
        campaign.status = campaign.Status.SENT
        campaign.recipients_sent = len(recipients)
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=["status", "recipients_sent", "sent_at"])

    return len(recipients)


def send_test_email(recipient_email: str) -> bool:
    """Dispatches an instant diagnostic test email to verify Brevo SMTP connection."""
    email_settings = get_email_settings()
    smtp_host = email_settings.smtp_host if email_settings else "smtp-relay.brevo.com"
    smtp_port = email_settings.smtp_port if email_settings else 587
    from_email = email_settings.from_email if email_settings else "care@mumagicmasala.com"

    send_templated_email(
        subject="Brevo SMTP Connection Test — MU Magic Masala",
        template_name="emails/test_email.html",
        context={
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "from_email": from_email,
            "timestamp": timezone.now().strftime("%d %b %Y, %I:%M:%S %p"),
            "preview_text": "Brevo SMTP connection verified successfully!",
        },
        recipient_list=[recipient_email],
        email_type="test",
        async_send=False,  # Synchronous so admin gets instant feedback
    )
    return True

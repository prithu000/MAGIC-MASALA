"""
apps/orders/invoice_service.py

Service for generating legally compliant Indian GST Tax Invoices for Mahila Udhyog.
Implements:
1. Sequential invoice number series (e.g. MU/26-27/0081).
2. 4-digit HSN mapping & reverse tax calculation (inclusive selling price -> taxable value + CGST/SGST/IGST).
3. Intra-state (UP: CGST 2.5% + SGST 2.5%) vs Interstate (Outside UP: IGST 5.0%).
4. Indian currency number to words conversion.
5. HSN-wise tax summary table required for GST registration and audits.
"""

from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from apps.core.models import SiteSettings


def num_to_indian_words(num_val):
    """
    Converts a Decimal/Float/Int number to Indian Currency words (Lakhs, Crores format).
    Example: 1450.50 -> 'Rupees One Thousand Four Hundred Fifty and Fifty Paise Only'
    """
    try:
        val = Decimal(str(num_val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return "Zero"

    rupees = int(val)
    paise = int(round((val - rupees) * 100))

    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_below_thousand(n):
        res = ""
        if n >= 100:
            res += ones[n // 100] + " Hundred "
            n %= 100
        if 0 < n < 20:
            res += ones[n] + " "
        elif n >= 20:
            res += tens[n // 10] + " "
            if n % 10 > 0:
                res += ones[n % 10] + " "
        return res.strip()

    if rupees == 0:
        words = "Zero"
    else:
        parts = []
        crores = rupees // 10000000
        rupees %= 10000000
        if crores:
            parts.append(convert_below_thousand(crores) + " Crore")

        lakhs = rupees // 100000
        rupees %= 100000
        if lakhs:
            parts.append(convert_below_thousand(lakhs) + " Lakh")

        thousands = rupees // 1000
        rupees %= 1000
        if thousands:
            parts.append(convert_below_thousand(thousands) + " Thousand")

        hundreds_and_below = rupees
        if hundreds_and_below:
            parts.append(convert_below_thousand(hundreds_and_below))

        words = " ".join(parts).strip()

    res_str = f"INR {words} Rupees"
    if paise > 0:
        res_str += f" and {convert_below_thousand(paise)} Paise"
    res_str += " Only"
    return res_str


def is_destination_uttar_pradesh(order):
    """
    Checks if shipping address is within Uttar Pradesh (Supplier state code 09).
    """
    state = (order.shipping_state or "").lower().strip()
    pincode = str(order.shipping_pincode or "").strip()
    
    # Common variations of Uttar Pradesh
    up_keywords = ["uttar pradesh", "uttarpradesh", "u.p", "up", "kasganj", "aligarh", "lucknow", "kanpur", "agra", "noida", "ghaziabad"]
    for kw in up_keywords:
        if kw == state or kw in state:
            return True
            
    # Indian pincodes starting with 20, 21, 22, 23, 24, 25, 26, 27, 28 belong to Uttar Pradesh / Uttarakhand
    # Kasganj is 207xxx
    if pincode.startswith(("20", "21", "22", "23", "24", "25", "26", "27", "28")):
        if "uttarakhand" not in state and "uk" != state:
            return True

    # If empty, treat as Uttar Pradesh
    if not state:
        return True

    return False


def get_or_generate_tax_invoice(order, force_regenerate=False):
    """
    Generates or fetches official sequential tax invoice for an order.
    Calculates exact GST line items and returns context dictionary for rendering/printing.
    """
    site_settings = SiteSettings.get_solo()
    
    # Determine interstate vs intra-state
    intra_state = is_destination_uttar_pradesh(order)
    order.is_interstate = not intra_state
    
    if not order.place_of_supply:
        order.place_of_supply = f"Uttar Pradesh (09)" if intra_state else f"{order.shipping_state or 'Interstate'}"
    if not order.transport_mode:
        order.transport_mode = "Road / Express Courier"
    if not order.vehicle_number:
        order.vehicle_number = order.tracking_number or "DL/UP-COMMERCIAL"

    # Assign invoice number if not already assigned
    if not order.invoice_number or force_regenerate:
        prefix = site_settings.invoice_prefix or "MU/26-27/"
        next_num = site_settings.next_invoice_number or 81
        order.invoice_number = f"{prefix}{next_num:04d}"
        order.invoice_date = timezone.localdate()
        
        # Increment sequence counter in site settings
        site_settings.next_invoice_number = next_num + 1
        site_settings.save(update_fields=["next_invoice_number"])

    if not order.invoice_date:
        order.invoice_date = timezone.localdate()

    # Recalculate tax breakdown per item
    # Retail prices in database are inclusive of GST
    total_taxable = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    total_igst = Decimal("0.00")

    hsn_summary = {}

    for item in order.items.all():
        # Ensure HSN and GST rate are correctly resolved
        if item.product and item.product.hsn_code:
            item.hsn_code = item.product.hsn_code
            gst_rate = item.product.gst_rate or Decimal("5.00")
        else:
            from apps.catalog.models import Product
            # Fallback search by product name keywords
            iname = (item.item_name or "").lower()
            clean_name = item.item_name.split("–")[0].split("-")[0].strip() if item.item_name else ""
            prod = Product.objects.filter(name__icontains=clean_name).first() if clean_name else None
            if prod:
                item.product = prod
                item.hsn_code = prod.hsn_code or "0910"
                gst_rate = prod.gst_rate or Decimal("5.00")
            elif any(k in iname for k in ["achaar", "pickle"]):
                item.hsn_code = "2001"
                gst_rate = Decimal("12.00")
            elif any(k in iname for k in ["namak", "salt"]):
                item.hsn_code = "2501"
                gst_rate = Decimal("5.00")
            elif any(k in iname for k in ["hing", "asafoetida"]):
                item.hsn_code = "1301"
                gst_rate = Decimal("5.00")
            elif any(k in iname for k in ["mirch", "chilli", "pepper"]):
                item.hsn_code = "0904"
                gst_rate = Decimal("5.00")
            elif any(k in iname for k in ["dhaniya", "jeera", "saunf", "coriander", "cumin", "fennel"]):
                item.hsn_code = "0909"
                gst_rate = Decimal("5.00")
            elif "dalchini" in iname or "cinnamon" in iname:
                item.hsn_code = "0906"
                gst_rate = Decimal("5.00")
            elif any(k in iname for k in ["garlic", "onion", "tomato"]):
                item.hsn_code = "0712"
                gst_rate = Decimal("5.00")
            else:
                item.hsn_code = "0910"
                gst_rate = Decimal("5.00")

        item.gst_rate = gst_rate

        line_total = item.line_total
        # Reverse calculate taxable value: LineTotal / (1 + Rate / 100)
        hundred = Decimal("100.00")
        factor = Decimal("1.00") + (gst_rate / hundred)
        taxable = (line_total / factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_amount = line_total - taxable

        item.taxable_value = taxable

        if order.is_interstate:
            item.igst_amount = tax_amount
            item.cgst_amount = Decimal("0.00")
            item.sgst_amount = Decimal("0.00")
            total_igst += tax_amount
        else:
            cgst = (tax_amount / Decimal("2.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sgst = tax_amount - cgst
            item.cgst_amount = cgst
            item.sgst_amount = sgst
            item.igst_amount = Decimal("0.00")
            total_cgst += cgst
            total_sgst += sgst

        total_taxable += taxable
        item.save()

        # Build HSN summary table
        hsn_key = (item.hsn_code, str(gst_rate))
        if hsn_key not in hsn_summary:
            hsn_summary[hsn_key] = {
                "hsn": item.hsn_code,
                "gst_rate": gst_rate,
                "taxable_value": Decimal("0.00"),
                "cgst_amount": Decimal("0.00"),
                "sgst_amount": Decimal("0.00"),
                "igst_amount": Decimal("0.00"),
                "total_tax": Decimal("0.00"),
            }
        hsn_summary[hsn_key]["taxable_value"] += item.taxable_value
        hsn_summary[hsn_key]["cgst_amount"] += item.cgst_amount
        hsn_summary[hsn_key]["sgst_amount"] += item.sgst_amount
        hsn_summary[hsn_key]["igst_amount"] += item.igst_amount
        hsn_summary[hsn_key]["total_tax"] += (item.cgst_amount + item.sgst_amount + item.igst_amount)

    order.taxable_amount = total_taxable
    order.cgst_amount = total_cgst
    order.sgst_amount = total_sgst
    order.igst_amount = total_igst

    items_sum = sum(item.line_total for item in order.items.all())
    if items_sum > Decimal("0.00"):
        order.subtotal = items_sum
        order.total = (
            order.subtotal
            + (order.shipping_charge or Decimal("0.00"))
            + (order.cod_charge_applied or Decimal("0.00"))
            - (order.discount_amount or Decimal("0.00"))
        )

    if order.payment_method == "cod":
        if not order.advance_amount or order.advance_amount == Decimal("0.00"):
            pct = Decimal(str(site_settings.cod_advance_percentage or 10.0))
            order.advance_amount = (order.total * pct / Decimal("100.00")).quantize(Decimal("0.01"))
            order.remaining_amount = order.total - order.advance_amount
    else:
        # Online / Prepaid: 100% prepaid
        order.advance_amount = order.total
        order.remaining_amount = Decimal("0.00")

    order.save(update_fields=[
        "invoice_number", "invoice_date", "is_interstate",
        "place_of_supply", "transport_mode", "vehicle_number",
        "taxable_amount", "cgst_amount", "sgst_amount", "igst_amount",
        "subtotal", "total", "advance_amount", "remaining_amount"
    ])

    amount_in_words = num_to_indian_words(order.total)

    # Format HSN list sorted
    hsn_list = sorted(hsn_summary.values(), key=lambda x: x["hsn"])

    # Effective tax rate label for display in summary box
    tax_rate_label = "2.5" if not order.is_interstate else "5.0"

    return {
        "order": order,
        "site_settings": site_settings,
        "items": order.items.all(),
        "hsn_list": hsn_list,
        "is_interstate": order.is_interstate,
        "tax_rate_label": tax_rate_label,
        "amount_in_words": amount_in_words,
        "copies": [
            {"title": "Original For Recipient", "color_badge": "White / Recipient"},
            {"title": "Duplicate For Transporter", "color_badge": "Pink / Transporter"},
            {"title": "Triplicate for Supplier", "color_badge": "Yellow / Supplier"},
        ],
    }

import os
import sys

sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib import admin

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    print("NO superuser found! Creating or finding staff user...")
    admin_user = User.objects.filter(is_staff=True).first()

print(f"Logged in as: {admin_user.email if admin_user else 'None'}")

client = Client()
if admin_user:
    client.force_login(admin_user)

print("\n" + "="*50)
print("TESTING USER SCREENSHOT URL: /admin/combos/customizecombOrule/")
print("="*50)
r_typo = client.get("/admin/combos/customizecombOrule/", follow=True)
print(f"  Result: HTTP {r_typo.status_code} (Redirect chain: {r_typo.redirect_chain})")
assert r_typo.status_code == 200, f"Expected 200 after follow, got {r_typo.status_code}"
print("  ✓ Capital 'O' URL successfully redirects and resolves with HTTP 200!")

print("\n" + "="*50)
print("TESTING UNFOLD SIDEBAR NAVIGATION LINKS")
print("="*50)

sidebar = settings.UNFOLD.get('SIDEBAR', {}).get('navigation', [])
failed_sidebar = []

for group in sidebar:
    g_title = group.get('title', 'Group')
    print(f"\n[{g_title}]")
    for item in group.get('items', []):
        title = item.get('title')
        link = item.get('link')
        try:
            resp = client.get(link, follow=True)
            status = resp.status_code
            last_url = resp.redirect_chain[-1][0] if resp.redirect_chain else link
            if status >= 400:
                print(f"  ❌ {title} -> {link} (HTTP {status})")
                failed_sidebar.append((title, link, status))
            else:
                print(f"  ✓ {title} -> {link} (HTTP {status})")
        except Exception as e:
            print(f"  ❌ {title} -> {link} (Exception: {e})")
            failed_sidebar.append((title, link, str(e)))

print("\n" + "="*50)
print("TESTING ALL REGISTERED ADMIN MODELS")
print("="*50)

failed_models = []
for model, model_admin in sorted(admin.site._registry.items(), key=lambda x: f"{x[0]._meta.app_label}.{x[0]._meta.model_name}"):
    opts = model._meta
    changelist_url = f"/admin/{opts.app_label}/{opts.model_name}/"
    add_url = f"/admin/{opts.app_label}/{opts.model_name}/add/"
    
    # Changelist
    try:
        r_list = client.get(changelist_url, follow=True)
        if r_list.status_code >= 400:
            print(f"  ❌ {opts.app_label}.{model.__name__} LIST -> {changelist_url} (HTTP {r_list.status_code})")
            failed_models.append((f"{opts.app_label}.{model.__name__} (list)", changelist_url, r_list.status_code))
        else:
            print(f"  ✓ {opts.app_label}.{model.__name__} LIST -> {changelist_url}")
    except Exception as e:
        print(f"  ❌ {opts.app_label}.{model.__name__} LIST -> Exception: {e}")
        failed_models.append((f"{opts.app_label}.{model.__name__} (list)", changelist_url, str(e)))

    # Add page (if allowed)
    try:
        r_add = client.get(add_url, follow=True)
        if r_add.status_code >= 400 and r_add.status_code != 403:  # 403 may be by design if has_add_permission returns False
            print(f"  ❌ {opts.app_label}.{model.__name__} ADD -> {add_url} (HTTP {r_add.status_code})")
            failed_models.append((f"{opts.app_label}.{model.__name__} (add)", add_url, r_add.status_code))
    except Exception as e:
        print(f"  ❌ {opts.app_label}.{model.__name__} ADD -> Exception: {e}")
        failed_models.append((f"{opts.app_label}.{model.__name__} (add)", add_url, str(e)))

print("\n" + "="*50)
print(f"SUMMARY: {len(failed_sidebar)} sidebar failures, {len(failed_models)} model failures")
print("="*50)
if failed_sidebar:
    print("Failed Sidebar links:")
    for f in failed_sidebar:
        print(" ", f)
if failed_models:
    print("Failed Model pages:")
    for f in failed_models:
        print(" ", f)

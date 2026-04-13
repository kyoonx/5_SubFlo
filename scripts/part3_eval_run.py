"""
One-off runner for Part 3 evaluation: email parser (4 bodies) + cancel-guide POST (1).
Usage from repo root: python scripts/part3_eval_run.py
"""
import json
import os
import sys
import time

# Repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SubFlo.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import Client

from subscriptions.email_parser import parse_email_to_json

EMAIL_PAID_NETFLIX = """Hi Alex,

Your Netflix membership has started.

Plan: Standard with Ads
Monthly price: $7.99
Start date: March 10, 2026
Next billing date: April 10, 2026
Payment method: Visa •••• 3847

Manage your account at www.netflix.com/account.
– Netflix"""

EMAIL_TRIAL_SPOTIFY = """Hey Maria,

Your 1-month free trial of Spotify Premium is now active!

Trial start: March 5, 2026
Trial end: April 5, 2026
Then $10.99/month unless you cancel.

– Spotify"""

EMAIL_PROMO_ONLY = """Subject: Limited time offer

Get 50% off your first order at ShopExample.com!
No subscription. Sale ends Friday.
Click here to browse deals."""

EMAIL_MESSY = """Welcome to Netflix!


Your Standard plan is now active as of March 2, 2026.


Price: $15.49/month
Next billing: April 2, 2026


Also you may like Netflix Games (separate).


Terms apply. © 2026 Netflix"""


def main():
    cases = [
        ("1_paid_netflix", EMAIL_PAID_NETFLIX),
        ("2_trial_spotify", EMAIL_TRIAL_SPOTIFY),
        ("3_promo_only", EMAIL_PROMO_ONLY),
        ("4_messy_netflix", EMAIL_MESSY),
    ]
    for name, body in cases:
        t0 = time.perf_counter()
        result = parse_email_to_json(body)
        dt = time.perf_counter() - t0
        print(f"=== {name} ({dt:.2f}s) ===", flush=True)
        print(json.dumps(result, indent=2, default=str), flush=True)
        print(flush=True)

    user, _ = User.objects.get_or_create(
        username="part3_eval_user",
        defaults={"email": "eval@example.com"},
    )
    user.set_password("part3_eval_pass")
    user.save()

    # development ALLOWED_HOSTS includes localhost, not default testserver
    client = Client(HTTP_HOST="localhost")
    assert client.login(username="part3_eval_user", password="part3_eval_pass")
    t0 = time.perf_counter()
    resp = client.post(
        "/subscriptions/cancel-guide/",
        data=json.dumps({"subscription_name": "Netflix"}),
        content_type="application/json",
    )
    dt = time.perf_counter() - t0
    print(f"=== 5_cancel_guide_netflix HTTP {resp.status_code} ({dt:.2f}s) ===", flush=True)
    try:
        print(json.dumps(resp.json(), indent=2, default=str)[:4000], flush=True)
    except Exception:
        print(resp.content[:2000], flush=True)


if __name__ == "__main__":
    main()

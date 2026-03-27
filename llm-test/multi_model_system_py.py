def main():
    # ============================================================
    # CATEGORY 1: CLASSIFICATION
    # Task: Is this email evidence that the user actively subscribes
    #       to a paid or trial service?  Answer: Yes or No.
    # ============================================================

    CLASSIFICATION_PROMPTS = [

        # Prompt C1 — Paid subscription confirmation
        {
            "id": "C1",
            "label": "Paid subscription confirmation",
            "expected_answer": "Yes",
            "prompt": """You are a subscription classification engine for a personal finance app.
    Your job is to decide whether the email below proves that the user currently holds
    an active subscription (trial OR paid) to a digital service.

    Rules:
    - Answer ONLY 'Yes' or 'No'.
    - 'Yes' means the user signed up and the service is active (including free trials).
    - 'No' means the email is an advertisement, a promotional offer, or a one-time purchase
    with no ongoing subscription.

    Email:
    From: "Netflix" <info@account.netflix.com>
    To: "Alex Rivera" <alex.rivera@gmail.com>
    Subject: Your Netflix Membership Has Started
    Date: Mon, 10 Mar 2026 11:05:33 -0600
    Message-ID: <NTFX-20260310-AR@netflix.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Alex,

    Welcome to Netflix! Your Standard with Ads plan is now active.

    Plan: Standard with Ads
    Monthly price: $7.99
    Start date: March 10, 2026
    Next billing date: April 10, 2026
    Payment method: Visa •••• 3847

    Enjoy unlimited movies and TV shows.
    Manage your account at www.netflix.com/account.

    – Netflix

    Answer (Yes/No):"""
        },

        # Prompt C2 — Free trial start
        {
            "id": "C2",
            "label": "Free trial start",
            "expected_answer": "Yes",
            "prompt": """You are a subscription classification engine for a personal finance app.
    Your job is to decide whether the email below proves that the user currently holds
    an active subscription (trial OR paid) to a digital service.

    Rules:
    - Answer ONLY 'Yes' or 'No'.
    - 'Yes' means the user signed up and the service is active (including free trials).
    - 'No' means the email is an advertisement, a promotional offer, or a one-time purchase
    with no ongoing subscription.

    Email:
    From: "Spotify" <no-reply@spotify.com>
    To: "Maria Chen" <mariachen22@outlook.com>
    Subject: Your Spotify Premium Free Trial Has Started
    Date: Thu, 05 Mar 2026 09:30:00 -0800
    Message-ID: <SPOT-20260305-MC@spotify.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hey Maria,

    Your 1-month free trial of Spotify Premium is now active!

    Trial start: March 5, 2026
    Trial ends: April 5, 2026
    After trial: $10.99/month (auto-renews unless cancelled)
    Payment method: Mastercard •••• 6621

    Cancel anytime before April 5 to avoid being charged.
    Manage your subscription: https://spotify.com/account/subscription

    Enjoy!
    – Spotify

    Answer (Yes/No):"""
        },

        # Prompt C3 — Advertisement disguised as service email (should be No)
        {
            "id": "C3",
            "label": "Promotional advertisement (not a subscription)",
            "expected_answer": "No",
            "prompt": """You are a subscription classification engine for a personal finance app.
    Your job is to decide whether the email below proves that the user currently holds
    an active subscription (trial OR paid) to a digital service.

    Rules:
    - Answer ONLY 'Yes' or 'No'.
    - 'Yes' means the user signed up and the service is active (including free trials).
    - 'No' means the email is an advertisement, a promotional offer, or a one-time purchase
    with no ongoing subscription.

    Email:
    From: "YouTube" <noreply@youtube.com>
    To: "Jordan Blake" <jordan.blake@gmail.com>
    Subject: Try YouTube TV — First 2 Months for $13.99/month!
    Date: Fri, 13 Mar 2026 16:44:10 -0500
    Message-ID: <YT-PROMO-20260313-JB@youtube.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Jordan,

    Sports, news, and live TV — all in one place.

    Sign up for YouTube TV and get your first 2 months for just $13.99/month
    (normally $72.99/month). Offer ends March 31, 2026.

    Start your trial: https://tv.youtube.com/welcome

    – The YouTube TV Team

    Answer (Yes/No):"""
        },

        # Prompt C4 — Medium email digest (not a subscription service)
        {
            "id": "C4",
            "label": "Medium digest email (not a subscription service)",
            "expected_answer": "No",
            "prompt": """You are a subscription classification engine for a personal finance app.
    Your job is to decide whether the email below proves that the user currently holds
    an active subscription (trial OR paid) to a digital service.

    Rules:
    - Answer ONLY 'Yes' or 'No'.
    - 'Yes' means the user signed up and the service is active (including free trials).
    - 'No' means the email is an advertisement, a promotional offer, newsletter, or digest
    with no billing confirmation.

    Email:
    From: "Medium Daily Digest" <noreply@medium.com>
    To: "Tom" <tom@example.com>
    Subject: Stories for Tom
    Date: Sun, 22 Mar 2026 08:00:00 -0500
    Message-ID: <MEDIUM-DIGEST-20260322@medium.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Today's highlights

    The CI/CD Setup That Cut Our Deployment Time from 40 Minutes to 8
    5 min read · 308 claps

    Forget ChatGPT & Gemini - Here Are New AI Tools That Will Blow Your Mind
    7 min read · 7.9K claps

    What Your Therapist Knows But Won't Tell You
    10 min read · 22K claps

    Sent by Medium · 3500 South DuPont Highway, Dover, DE 19901
    Unsubscribe from this type of email.

    Answer (Yes/No):"""
        },

        # Prompt C5 — Subscription cancellation confirmation (service was active but is now cancelled)
        {
            "id": "C5",
            "label": "Cancellation confirmation (no longer active)",
            "expected_answer": "No",
            "prompt": """You are a subscription classification engine for a personal finance app.
    Your job is to decide whether the email below proves that the user currently holds
    an active subscription (trial OR paid) to a digital service.

    Rules:
    - Answer ONLY 'Yes' or 'No'.
    - 'Yes' means the user signed up and the service is currently active (including free trials).
    - 'No' means the subscription has been cancelled, expired, or the email is not a billing confirmation.

    Email:
    From: "Adobe" <adobe@adobe.com>
    To: "Kevin Park" <kevinp88@gmail.com>
    Subject: Your Adobe Creative Cloud subscription has been cancelled
    Date: Tue, 18 Mar 2026 13:22:45 -0700
    Message-ID: <ADOBE-CANCEL-20260318-KP@adobe.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Kevin,

    We've processed your cancellation request for Adobe Creative Cloud.

    Your subscription will remain active through the end of your current billing period: March 31, 2026.
    After that date, you will no longer be charged and your access will end.

    Plan: Creative Cloud All Apps
    Final billing date: March 1, 2026
    Access ends: March 31, 2026

    If you change your mind, you can resubscribe at any time at adobe.com/creativecloud.

    – Adobe

    Answer (Yes/No):"""
        },

    ]

    print(f"Classification prompts loaded: {len(CLASSIFICATION_PROMPTS)}")
    for p in CLASSIFICATION_PROMPTS:
        print(f"  [{p['id']}] {p['label']} → expected: {p['expected_answer']}")
    
    
    # ============================================================
    # CATEGORY 2: PREDICTION
    # Task: Given a subscription email that does NOT explicitly
    #       state the next billing date, predict when it will be.
    # ============================================================

    PREDICTION_PROMPTS = [

        # Prompt P1 — Monthly plan, start date given, no next date
        {
            "id": "P1",
            "label": "Monthly plan, predict next billing from start date",
            "prompt": """You are a billing-date prediction assistant.
    Given the subscription email below, predict the NEXT charge date.
    The email does NOT contain an explicit next billing date field.
    Use the start date and billing cycle to infer it.

    Return ONLY a JSON object: { "next_billing_date": "YYYY-MM-DD", "reasoning": "<one sentence>" }

    Email:
    From: "Hulu" <noreply@hulu.com>
    To: "Priya Nair" <priya.nair@gmail.com>
    Subject: Welcome to Hulu — Subscription Active
    Date: Sat, 07 Mar 2026 10:15:00 -0600
    Message-ID: <HULU-20260307-PN@hulu.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Priya,

    Your Hulu (No Ads) plan is now active as of March 7, 2026.
    You will be billed $17.99 each month.
    Payment method: Visa •••• 1123

    Manage your subscription at hulu.com/account.
    – Hulu

    JSON output:"""
        },

        # Prompt P2 — Annual plan, predict 12-month renewal
        {
            "id": "P2",
            "label": "Annual plan, predict next billing from start date",
            "prompt": """You are a billing-date prediction assistant.
    Given the subscription email below, predict the NEXT charge date.
    The email does NOT contain an explicit next billing date field.
    Use the start date and billing cycle to infer it.

    Return ONLY a JSON object: { "next_billing_date": "YYYY-MM-DD", "reasoning": "<one sentence>" }

    Email:
    From: "iCloud" <no_reply@email.apple.com>
    To: "Sam Torres" <sam.torres77@icloud.com>
    Subject: Your iCloud+ 2TB Plan Is Active
    Date: Mon, 02 Feb 2026 14:00:00 -0800
    Message-ID: <APPLE-ICLOUD-20260202-ST@apple.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Sam,

    Thank you for upgrading to iCloud+ 2TB.
    Your plan started on February 2, 2026.
    Annual plan price: $35.88/year
    Payment method: Apple Pay — Mastercard •••• 4499

    Manage storage at apple.com/icloud.
    – Apple

    JSON output:"""
        },

        # Prompt P3 — Trial ending, predict first charge date after trial
        {
            "id": "P3",
            "label": "Trial period, predict first charge date after trial ends",
            "prompt": """You are a billing-date prediction assistant.
    Given the subscription email below, predict the date of the FIRST real charge
    (i.e., when the trial ends and billing begins).
    Return ONLY a JSON object: { "next_billing_date": "YYYY-MM-DD", "reasoning": "<one sentence>" }

    Email:
    From: "Amazon Prime" <no-reply@amazon.com>
    To: "Lisa Wong" <lisawong90@gmail.com>
    Subject: Your Amazon Prime 30-Day Free Trial Has Begun
    Date: Wed, 11 Mar 2026 08:55:00 -0500
    Message-ID: <AMZN-PRIME-20260311-LW@amazon.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Lisa,

    Your free 30-day Amazon Prime trial started today, March 11, 2026.
    After your trial, membership is $14.99/month.
    Payment method on file: Discover •••• 8823
    Cancel before your trial ends to avoid charges.

    Visit amazon.com/prime to manage your membership.
    – Amazon

    JSON output:"""
        },

        # Prompt P4 — Quarterly billing cycle
        {
            "id": "P4",
            "label": "Quarterly billing, predict next charge",
            "prompt": """You are a billing-date prediction assistant.
    Given the subscription email below, predict the NEXT charge date.
    The email does NOT contain an explicit next billing date.
    Use the start date and billing cycle description to infer it.

    Return ONLY a JSON object: { "next_billing_date": "YYYY-MM-DD", "reasoning": "<one sentence>" }

    Email:
    From: "Duolingo" <no-reply@duolingo.com>
    To: "Ethan Brooks" <ethanbrooks@yahoo.com>
    Subject: Duolingo Super — Quarterly Plan Activated
    Date: Tue, 03 Mar 2026 17:00:00 -0600
    Message-ID: <DUOLINGO-20260303-EB@duolingo.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Ethan,

    You're now on Duolingo Super — Quarterly Plan!
    Activated: March 3, 2026
    Price: $29.99 every 3 months
    Payment method: PayPal

    Manage your plan at duolingo.com/settings/super.
    – Duolingo Team

    JSON output:"""
        },

        # Prompt P5 — Medium digest (real attached sample), no billing at all — should predict null
        {
            "id": "P5",
            "label": "Non-billing email (newsletter), expect null prediction",
            "prompt": """You are a billing-date prediction assistant.
    Given the subscription email below, predict the NEXT charge date.
    If the email contains no billing or subscription payment information,
    set next_billing_date to null and explain why in reasoning.

    Return ONLY a JSON object: { "next_billing_date": null or "YYYY-MM-DD", "reasoning": "<one sentence>" }

    Email:
    From: "Medium Daily Digest" <noreply@medium.com>
    To: "Tom" <tom@example.com>
    Subject: Stories for Tom
    Date: Sun, 22 Mar 2026 08:00:00 -0500
    Message-ID: <MEDIUM-DIGEST-20260322@medium.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Today's highlights

    The CI/CD Setup That Cut Our Deployment Time from 40 Minutes to 8 — 5 min read
    Forget ChatGPT & Gemini - Here Are New AI Tools That Will Blow Your Mind — 7 min read
    Senior Developers Are Becoming the New Juniors (And No One's Ready) — 5 min read
    Building AI Agents in 2026: Chatbots to Agentic Architectures — 34 min read

    Sent by Medium · Unsubscribe from this type of email.

    JSON output:"""
        },

    ]

    print(f"Prediction prompts loaded: {len(PREDICTION_PROMPTS)}")
    for p in PREDICTION_PROMPTS:
        print(f"  [{p['id']}] {p['label']}")
            
    
    
    
    
    # ============================================================
    # CATEGORY 3: SUMMARIZATION
    # Task: Compress a raw subscription email into a short,
    #       human-readable summary (2–3 sentences max).
    # ============================================================

    SUMMARIZATION_PROMPTS = [

        # Prompt S1 — Paid subscription with billing details
        {
            "id": "S1",
            "label": "Paid subscription summary",
            "prompt": """Summarize the subscription email below in 2–3 plain English sentences.
    Include: the service name, whether it is a trial or paid plan, the price, and the next billing date if mentioned.
    Do NOT copy full sentences from the email — write your own concise summary.

    Email:
    From: "YouTube" <no-reply@youtube.com>
    To: "Daniel Harper" <daniel.harper93@gmail.com>
    Subject: Welcome to YouTube Premium – Your Membership Is Active
    Date: Mon, 02 Mar 2026 09:14:22 -0600
    Message-ID: <20260302091422.987654321@mail.youtube.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Daniel,

    Thanks for becoming a YouTube Premium member.

    Your membership is now active as of March 2, 2026.

    Plan: Individual Plan
    Price: $13.99/month
    Next billing date: April 2, 2026
    Payment method: Visa •••• 4821

    You can manage your membership anytime in your YouTube settings.
    Enjoy ad-free videos, background play, and YouTube Music Premium.

    – The YouTube Team

    Summary:"""
        },

        # Prompt S2 — Free trial with end date
        {
            "id": "S2",
            "label": "Free trial summary with end date",
            "prompt": """Summarize the subscription email below in 2–3 plain English sentences.
    Include: the service name, that it is a free trial, when the trial ends, and the post-trial price.
    Do NOT copy full sentences from the email — write your own concise summary.

    Email:
    From: "Spotify" <no-reply@spotify.com>
    To: "Sarah Johnson" <sarah.j.1995@outlook.com>
    Subject: Your Spotify Premium Free Trial Has Started
    Date: Fri, 06 Mar 2026 14:28:55 -0800
    Message-ID: <20260306142855.123456789@mail.spotify.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hey Sarah,

    Your Spotify Premium free trial is now active!

    Trial start date: March 6, 2026
    Trial end date: April 6, 2026
    After trial: $10.99/month
    Payment method: Mastercard •••• 3392

    Cancel anytime before April 6 to avoid charges.

    Manage subscription: https://spotify.com/account/subscription

    Happy listening!
    Spotify

    Summary:"""
        },

        # Prompt S3 — Annual subscription with renewal warning
        {
            "id": "S3",
            "label": "Annual subscription renewal reminder summary",
            "prompt": """Summarize the subscription email below in 2–3 plain English sentences.
    Include: the service name, the renewal date, the price, and any action required.
    Do NOT copy full sentences from the email — write your own concise summary.

    Email:
    From: "Microsoft" <microsoft-noreply@microsoft.com>
    To: "Nina Patel" <ninapatel@hotmail.com>
    Subject: Your Microsoft 365 subscription renews soon
    Date: Fri, 20 Mar 2026 10:00:00 -0500
    Message-ID: <MSFT-365-20260320-NP@microsoft.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Nina,

    Your Microsoft 365 Personal subscription is set to auto-renew.

    Renewal date: April 1, 2026
    Annual price: $69.99
    Payment method: Visa •••• 5512

    If you do not want to renew, cancel before March 31, 2026 at account.microsoft.com.

    – Microsoft

    Summary:"""
        },

        # Prompt S4 — Cancellation confirmation (edge case)
        {
            "id": "S4",
            "label": "Cancellation confirmation summary",
            "prompt": """Summarize the subscription email below in 2–3 plain English sentences.
    Include: the service name, that the subscription was cancelled, when access ends.
    Do NOT copy full sentences from the email — write your own concise summary.

    Email:
    From: "Adobe" <adobe@adobe.com>
    To: "Kevin Park" <kevinp88@gmail.com>
    Subject: Your Adobe Creative Cloud subscription has been cancelled
    Date: Tue, 18 Mar 2026 13:22:45 -0700
    Message-ID: <ADOBE-CANCEL-20260318-KP@adobe.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Kevin,

    We've processed your cancellation request for Adobe Creative Cloud.

    Your subscription will remain active through the end of your current billing period: March 31, 2026.
    After that date, you will no longer be charged and your access will end.

    Plan: Creative Cloud All Apps
    Final billing date: March 1, 2026
    Access ends: March 31, 2026

    If you change your mind, resubscribe at adobe.com/creativecloud.

    – Adobe

    Summary:"""
        },

        # Prompt S5 — Medium newsletter digest (real attached sample)
        {
            "id": "S5",
            "label": "Newsletter digest summary (non-subscription)",
            "prompt": """Summarize the email below in 2–3 plain English sentences.
    Describe what type of email this is, who sent it, and its general content.
    Do NOT copy full sentences from the email — write your own concise summary.

    Email:
    From: "Medium Daily Digest" <noreply@medium.com>
    To: "Tom" <tom@example.com>
    Subject: Stories for Tom
    Date: Sun, 22 Mar 2026 08:00:00 -0500
    Message-ID: <MEDIUM-DIGEST-20260322@medium.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Today's highlights

    The CI/CD Setup That Cut Our Deployment Time from 40 Minutes to 8 — by Bhavyansh — 5 min read · 308 claps
    Forget ChatGPT & Gemini - Here Are New AI Tools That Will Blow Your Mind — by Nitin Sharma — 7 min read · 7.9K claps
    What Your Therapist Knows But Won't Tell You: Confessions From Inside the... — by Constantin Patrascu — 10 min read · 22K claps
    Building the 7 Layers of a Production-Grade Agentic AI System — by Fareed Khan — 63 min read · 1.8K claps
    5 Obvious Ways Everyone Knows You're Using ChatGPT — by Joe Procopio — 7 min read · 12.9K claps
    Senior Developers Are Becoming the New Juniors (And No One's Ready) — by Adonis — 5 min read · 1.4K claps

    Sent by Medium · 3500 South DuPont Highway, Dover, DE 19901

    Summary:"""
        },

    ]

    print(f"Summarization prompts loaded: {len(SUMMARIZATION_PROMPTS)}")
    for p in SUMMARIZATION_PROMPTS:
        print(f"  [{p['id']}] {p['label']}")
        


    # ============================================================
    # CATEGORY 4: TEXT GENERATION
    # Task: Generate a step-by-step cancellation guide
    #       for the service identified in the email.
    #       Mirrors the logic in subscriptions/ai_guide_view.py.
    # ============================================================

    TEXT_GENERATION_PROMPTS = [

        # Prompt T1 — Netflix cancellation guide
        {
            "id": "T1",
            "label": "Netflix cancellation guide",
            "prompt": """You are a consumer-rights assistant that helps users cancel unwanted subscriptions.
    Your tone is clear, friendly, and step-by-step.
    Do NOT include personal opinions, marketing language, or off-topic content.

    The user received the following subscription confirmation email:

    From: "Netflix" <info@account.netflix.com>
    To: "Christopher Martinez" <cmartinez91@yahoo.com>
    Subject: Your Netflix Membership Has Started
    Date: Wed, 04 Mar 2026 18:42:17 -0500

    Hi Christopher,
    Welcome to Netflix! Your Standard Plan membership is now active.
    Monthly price: $15.49 | Next billing date: April 4, 2026
    Payment method: Discover •••• 7712

    SERVICE NAME: Netflix

    TASK: Write a numbered, step-by-step guide (maximum 10 steps) explaining exactly
    how the user can cancel their Netflix subscription.
    Include:
    1. The official cancellation URL or app path
    2. Estimated time to complete
    3. Any common traps (e.g. 'pause instead of cancel' dark patterns)
    4. What confirmation to look for

    Format your response ONLY as a JSON object:
    {
    "service": "<service name>",
    "estimated_time": "<e.g. 2 minutes>",
    "cancellation_url": "<direct URL or 'In-app only'>",
    "steps": ["Step 1 text", "Step 2 text", ...],
    "warnings": ["Warning 1", ...]
    }
    Return ONLY valid JSON. No markdown, no preamble."""
        },

        # Prompt T2 — Spotify cancellation guide
        {
            "id": "T2",
            "label": "Spotify cancellation guide (trial)",
            "prompt": """You are a consumer-rights assistant that helps users cancel unwanted subscriptions.
    Your tone is clear, friendly, and step-by-step.
    Do NOT include personal opinions, marketing language, or off-topic content.

    The user received the following subscription confirmation email:

    From: "Spotify" <no-reply@spotify.com>
    To: "Sarah Johnson" <sarah.j.1995@outlook.com>
    Subject: Your Spotify Premium Free Trial Has Started
    Date: Fri, 06 Mar 2026 14:28:55 -0800

    Hey Sarah,
    Your Spotify Premium free trial is now active!
    Trial end date: April 6, 2026 | After trial: $10.99/month

    SERVICE NAME: Spotify Premium

    TASK: Write a numbered, step-by-step guide (maximum 10 steps) explaining exactly
    how the user can cancel their Spotify Premium subscription before the trial ends.
    Include:
    1. The official cancellation URL or app path
    2. Estimated time to complete
    3. Any common traps (e.g. 'pause instead of cancel' dark patterns)
    4. What confirmation to look for

    Format your response ONLY as a JSON object:
    {
    "service": "<service name>",
    "estimated_time": "<e.g. 2 minutes>",
    "cancellation_url": "<direct URL or 'In-app only'>",
    "steps": ["Step 1 text", "Step 2 text", ...],
    "warnings": ["Warning 1", ...]
    }
    Return ONLY valid JSON. No markdown, no preamble."""
        },

        # Prompt T3 — Adobe Creative Cloud cancellation guide (known dark patterns)
        {
            "id": "T3",
            "label": "Adobe Creative Cloud cancellation guide (dark patterns)",
            "prompt": """You are a consumer-rights assistant that helps users cancel unwanted subscriptions.
    Your tone is clear, friendly, and step-by-step.
    Do NOT include personal opinions, marketing language, or off-topic content.

    The user received the following subscription confirmation email:

    From: "Adobe" <adobe@adobe.com>
    To: "Kevin Park" <kevinp88@gmail.com>
    Subject: Adobe Creative Cloud — All Apps Plan Active
    Date: Mon, 02 Feb 2026 09:00:00 -0700

    Hi Kevin,
    Your Adobe Creative Cloud All Apps subscription is now active.
    Monthly price: $59.99 | Next billing date: March 2, 2026
    Payment method: Visa •••• 2211

    SERVICE NAME: Adobe Creative Cloud

    TASK: Write a numbered, step-by-step guide (maximum 10 steps) explaining exactly
    how the user can cancel their Adobe Creative Cloud subscription.
    Include:
    1. The official cancellation URL or app path
    2. Estimated time to complete
    3. Any common traps (Adobe is known for cancellation fees and retention tactics)
    4. What confirmation to look for

    Format your response ONLY as a JSON object:
    {
    "service": "<service name>",
    "estimated_time": "<e.g. 2 minutes>",
    "cancellation_url": "<direct URL or 'In-app only'>",
    "steps": ["Step 1 text", "Step 2 text", ...],
    "warnings": ["Warning 1", ...]
    }
    Return ONLY valid JSON. No markdown, no preamble."""
        },

        # Prompt T4 — Amazon Prime cancellation guide
        {
            "id": "T4",
            "label": "Amazon Prime cancellation guide",
            "prompt": """You are a consumer-rights assistant that helps users cancel unwanted subscriptions.
    Your tone is clear, friendly, and step-by-step.
    Do NOT include personal opinions, marketing language, or off-topic content.

    The user received the following subscription confirmation email:

    From: "Amazon Prime" <no-reply@amazon.com>
    To: "Lisa Wong" <lisawong90@gmail.com>
    Subject: Your Amazon Prime 30-Day Free Trial Has Begun
    Date: Wed, 11 Mar 2026 08:55:00 -0500

    Hi Lisa,
    Your Amazon Prime 30-day free trial started March 11, 2026.
    After trial: $14.99/month
    Cancel before trial ends to avoid charges.

    SERVICE NAME: Amazon Prime

    TASK: Write a numbered, step-by-step guide (maximum 10 steps) explaining exactly
    how the user can cancel their Amazon Prime membership.
    Include:
    1. The official cancellation URL or app path
    2. Estimated time to complete
    3. Any common traps (Amazon uses a multi-step confirmation with retain offers)
    4. What confirmation to look for

    Format your response ONLY as a JSON object:
    {
    "service": "<service name>",
    "estimated_time": "<e.g. 2 minutes>",
    "cancellation_url": "<direct URL or 'In-app only'>",
    "steps": ["Step 1 text", "Step 2 text", ...],
    "warnings": ["Warning 1", ...]
    }
    Return ONLY valid JSON. No markdown, no preamble."""
        },

        # Prompt T5 — YouTube Premium cancellation guide
        {
            "id": "T5",
            "label": "YouTube Premium cancellation guide",
            "prompt": """You are a consumer-rights assistant that helps users cancel unwanted subscriptions.
    Your tone is clear, friendly, and step-by-step.
    Do NOT include personal opinions, marketing language, or off-topic content.

    The user received the following subscription confirmation email:

    From: "YouTube" <no-reply@youtube.com>
    To: "Daniel Harper" <daniel.harper93@gmail.com>
    Subject: Welcome to YouTube Premium – Your Membership Is Active
    Date: Mon, 02 Mar 2026 09:14:22 -0600

    Hi Daniel,
    Your YouTube Premium Individual Plan is now active.
    Price: $13.99/month | Next billing date: April 2, 2026
    Payment method: Visa •••• 4821

    SERVICE NAME: YouTube Premium

    TASK: Write a numbered, step-by-step guide (maximum 10 steps) explaining exactly
    how the user can cancel their YouTube Premium subscription.
    Include:
    1. The official cancellation URL or app path
    2. Estimated time to complete
    3. Any common traps
    4. What confirmation to look for

    Format your response ONLY as a JSON object:
    {
    "service": "<service name>",
    "estimated_time": "<e.g. 2 minutes>",
    "cancellation_url": "<direct URL or 'In-app only'>",
    "steps": ["Step 1 text", "Step 2 text", ...],
    "warnings": ["Warning 1", ...]
    }
    Return ONLY valid JSON. No markdown, no preamble."""
        },

    ]

    print(f"Text generation prompts loaded: {len(TEXT_GENERATION_PROMPTS)}")
    for p in TEXT_GENERATION_PROMPTS:
        print(f"  [{p['id']}] {p['label']}")




    # ============================================================
    # CATEGORY 5: STRUCTURED EXTRACTION
    # Task: Parse a raw subscription email into the Subscription
    #       model schema used by SubFlo.
    #
    # Schema fields:
    #   platform_name, service_name, start_date, end_date,
    #   is_trial, already_canceled, price, currency,
    #   payment_method, unsubscribe_link
    # ============================================================

    STRUCTURED_EXTRACTION_PROMPTS = [

        # Prompt E1 — Paid subscription (YouTube Premium)
        {
            "id": "E1",
            "label": "Paid subscription extraction (YouTube Premium)",
            "prompt": """Extract the following fields from the subscription email below and return ONLY a valid JSON object.

    Fields:
    - platform_name: Name of the service platform (string)
    - service_name: Specific plan or tier name (string)
    - start_date: Subscription start date in YYYY-MM-DD format (string)
    - end_date: Subscription end/expiry date in YYYY-MM-DD format, or null if not mentioned
    - is_trial: true if this is a free trial, false if paid (boolean)
    - already_canceled: true if the email confirms a cancellation, false otherwise (boolean)
    - price: Recurring price as a decimal number (float)
    - currency: ISO currency code, e.g. 'USD' (string)
    - payment_method: Payment method description (string)
    - unsubscribe_link: Direct cancellation/management URL if present, otherwise null

    Email:
    From: "YouTube" <no-reply@youtube.com>
    To: "Daniel Harper" <daniel.harper93@gmail.com>
    Subject: Welcome to YouTube Premium – Your Membership Is Active
    Date: Mon, 02 Mar 2026 09:14:22 -0600
    Message-ID: <20260302091422.987654321@mail.youtube.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Daniel,

    Thanks for becoming a YouTube Premium member.

    Your membership is now active as of March 2, 2026.

    Plan: Individual Plan
    Price: $13.99/month
    Next billing date: April 2, 2026
    Payment method: Visa •••• 4821

    You can manage your membership anytime in your YouTube settings.
    Enjoy ad-free videos, background play, and YouTube Music Premium.

    – The YouTube Team

    JSON output:"""
        },

        # Prompt E2 — Free trial extraction (Spotify)
        {
            "id": "E2",
            "label": "Free trial extraction (Spotify Premium)",
            "prompt": """Extract the following fields from the subscription email below and return ONLY a valid JSON object.

    Fields:
    - platform_name: Name of the service platform (string)
    - service_name: Specific plan or tier name (string)
    - start_date: Subscription start date in YYYY-MM-DD format (string)
    - end_date: Trial end date in YYYY-MM-DD format, or null if not mentioned
    - is_trial: true if this is a free trial, false if paid (boolean)
    - already_canceled: true if the email confirms a cancellation, false otherwise (boolean)
    - price: Post-trial recurring price as a decimal number (float)
    - currency: ISO currency code (string)
    - payment_method: Payment method description (string)
    - unsubscribe_link: Direct cancellation/management URL if present, otherwise null

    Email:
    From: "Spotify" <no-reply@spotify.com>
    To: "Sarah Johnson" <sarah.j.1995@outlook.com>
    Subject: Your Spotify Premium Free Trial Has Started
    Date: Fri, 06 Mar 2026 14:28:55 -0800
    Message-ID: <20260306142855.123456789@mail.spotify.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hey Sarah,

    Your Spotify Premium free trial is now active!

    Trial start date: March 6, 2026
    Trial end date: April 6, 2026
    After trial: $10.99/month
    Payment method: Mastercard •••• 3392

    Cancel anytime before April 6 to avoid charges.

    Manage subscription: https://spotify.com/account/subscription

    Happy listening!
    Spotify

    JSON output:"""
        },

        # Prompt E3 — Cancellation confirmation (Adobe), already_canceled = true
        {
            "id": "E3",
            "label": "Cancellation confirmation extraction (Adobe CC)",
            "prompt": """Extract the following fields from the subscription email below and return ONLY a valid JSON object.

    Fields:
    - platform_name: Name of the service platform (string)
    - service_name: Specific plan or tier name (string)
    - start_date: Original subscription start date in YYYY-MM-DD, or null if not mentioned
    - end_date: Date access ends in YYYY-MM-DD format, or null
    - is_trial: true if this was a trial, false otherwise (boolean)
    - already_canceled: true if the email confirms a cancellation (boolean)
    - price: Last known recurring price as decimal, or null
    - currency: ISO currency code (string)
    - payment_method: Payment method description, or null
    - unsubscribe_link: Resubscribe/manage URL if present, otherwise null

    Email:
    From: "Adobe" <adobe@adobe.com>
    To: "Kevin Park" <kevinp88@gmail.com>
    Subject: Your Adobe Creative Cloud subscription has been cancelled
    Date: Tue, 18 Mar 2026 13:22:45 -0700
    Message-ID: <ADOBE-CANCEL-20260318-KP@adobe.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Kevin,

    We've processed your cancellation request for Adobe Creative Cloud.

    Your subscription will remain active through March 31, 2026.
    After that date, you will no longer be charged and your access will end.

    Plan: Creative Cloud All Apps
    Final billing date: March 1, 2026
    Access ends: March 31, 2026

    If you change your mind, resubscribe at adobe.com/creativecloud.

    – Adobe

    JSON output:"""
        },

        # Prompt E4 — Netflix paid subscription (clean email with all fields)
        {
            "id": "E4",
            "label": "Paid subscription extraction (Netflix Standard)",
            "prompt": """Extract the following fields from the subscription email below and return ONLY a valid JSON object.

    Fields:
    - platform_name: Name of the service platform (string)
    - service_name: Specific plan or tier name (string)
    - start_date: Subscription start date in YYYY-MM-DD format (string)
    - end_date: Subscription end date in YYYY-MM-DD format, or null if not applicable
    - is_trial: true if this is a free trial, false if paid (boolean)
    - already_canceled: true if the email confirms a cancellation, false otherwise (boolean)
    - price: Recurring price as a decimal number (float)
    - currency: ISO currency code (string)
    - payment_method: Payment method description (string)
    - unsubscribe_link: Direct cancellation/management URL if present, otherwise null

    Email:
    From: "Netflix" <info@account.netflix.com>
    To: "Christopher Martinez" <cmartinez91@yahoo.com>
    Subject: Your Netflix Membership Has Started
    Date: Wed, 04 Mar 2026 18:42:17 -0500
    Message-ID: <4F2A8B91-NTFX-2026@netflix.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Hi Christopher,

    Welcome to Netflix!

    Your Standard Plan membership is now active.

    Monthly price: $15.49
    Next billing date: April 4, 2026
    Payment method: Discover •••• 7712

    Start watching anytime at www.netflix.com.

    Happy streaming,
    Netflix

    JSON output:"""
        },

        # Prompt E5 — Medium newsletter (no subscription fields — should return nulls/false)
        {
            "id": "E5",
            "label": "Non-subscription email extraction (Medium digest)",
            "prompt": """Extract the following fields from the email below and return ONLY a valid JSON object.
    If a field cannot be determined from the email, use null for strings/dates and false for booleans.

    Fields:
    - platform_name: Name of the sender platform (string)
    - service_name: Specific plan or tier, or null
    - start_date: Subscription start date in YYYY-MM-DD, or null
    - end_date: Subscription end date in YYYY-MM-DD, or null
    - is_trial: true if this is a free trial, false otherwise (boolean)
    - already_canceled: true if a cancellation is confirmed, false otherwise (boolean)
    - price: Price as decimal, or null if no billing info
    - currency: ISO currency code, or null
    - payment_method: Payment method, or null
    - unsubscribe_link: Unsubscribe URL if present, otherwise null

    Email:
    From: "Medium Daily Digest" <noreply@medium.com>
    To: "Tom" <tom@example.com>
    Subject: Stories for Tom
    Date: Sun, 22 Mar 2026 08:00:00 -0500
    Message-ID: <MEDIUM-DIGEST-20260322@medium.com>
    MIME-Version: 1.0
    Content-Type: text/plain; charset="UTF-8"

    Today's highlights

    The CI/CD Setup That Cut Our Deployment Time from 40 Minutes to 8 — 5 min read · 308 claps
    Forget ChatGPT & Gemini - Here Are New AI Tools That Will Blow Your Mind — 7 min read · 7.9K claps
    What Your Therapist Knows But Won't Tell You — 10 min read · 22K claps
    Building the 7 Layers of a Production-Grade Agentic AI System — 63 min read · 1.8K claps
    5 Obvious Ways Everyone Knows You're Using ChatGPT — 7 min read · 12.9K claps
    Senior Developers Are Becoming the New Juniors (And No One's Ready) — 5 min read · 1.4K claps

    Sent by Medium · 3500 South DuPont Highway, Dover, DE 19901
    Unsubscribe: https://medium.com/me/email-settings/29ee627ca4b0/cb45d6b33f89

    JSON output:"""
        },

    ]

    print(f"Structured extraction prompts loaded: {len(STRUCTURED_EXTRACTION_PROMPTS)}")
    for p in STRUCTURED_EXTRACTION_PROMPTS:
        print(f"  [{p['id']}] {p['label']}")



    # ============================================================
    # COMBINED PROMPT REGISTRY
    # All 25 prompts indexed by category for use in Part 1.5.
    # ============================================================

    ALL_PROMPTS = {
        "classification":       CLASSIFICATION_PROMPTS,        # C1–C5
        "prediction":           PREDICTION_PROMPTS,            # P1–P5
        "summarization":        SUMMARIZATION_PROMPTS,         # S1–S5
        "text_generation":      TEXT_GENERATION_PROMPTS,       # T1–T5
        "structured_extraction": STRUCTURED_EXTRACTION_PROMPTS # E1–E5
    }

    total = sum(len(v) for v in ALL_PROMPTS.values())
    print(f"Total prompts loaded: {total}")
    for category, prompts in ALL_PROMPTS.items():
        print(f"  {category}: {len(prompts)} prompts")



    # ============================================================
    # IMPORTS & SETUP
    # ============================================================
    import time
    import platform
    import psutil
    import torch
    import pandas as pd
    import warnings
    import gc
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

    warnings.filterwarnings('ignore')

    # ── Device detection (same as section-3-week-7.ipynb) ──────────────────────
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    print(f"Using device: {device}")

    # ── Hardware info (mirrored from section-3-week-7.ipynb) ───────────────────
    def print_hardware_info():
        os_name   = f"{platform.system()} {platform.release()}"
        cpu_name  = platform.processor()
        cpu_cores = psutil.cpu_count(logical=True)
        ram_gb    = round(psutil.virtual_memory().total / (1024**3), 2)
        if device == "cuda":
            gpu_name    = torch.cuda.get_device_name(0)
            device_name = "CUDA GPU"
        elif device == "mps":
            gpu_name    = "Apple Silicon GPU"
            device_name = "Apple Silicon (MPS)"
        else:
            gpu_name    = "None"
            device_name = "CPU"
        print("\n" + "="*65)
        print("SYSTEM HARDWARE INFORMATION".center(65))
        print("="*65)
        print(f"{'Operating System':<20} : {os_name}")
        print(f"{'Processor':<20} : {cpu_name}")
        print(f"{'CPU Cores':<20} : {cpu_cores}")
        print(f"{'RAM (GB)':<20} : {ram_gb}")
        print(f"{'GPU':<20} : {gpu_name}")
        print(f"{'Compute Device':<20} : {device_name}")
        print("="*65 + "\n")

    print_hardware_info()





    # ============================================================
    # MODEL REGISTRY
    # 15 models × 5 categories from A6 / Part 1.1
    # (exact IDs as used in ai_prototype.ipynb)
    #
    # loader: "auto"     → AutoModelForCausalLM + apply_chat_template
    #         "pipeline" → transformers text-generation pipeline
    # ============================================================

    MODEL_REGISTRY = [

        # ── Ultra-Light  < 1B ──────────────────────────────────────────────────
        {
            "hf_id":    "qwen/Qwen2.5-0.5B-Instruct",
            "category": "Ultra-Light",
            "loader":   "auto",
        },
        {
            "hf_id":    "JayHyeon/Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam",
            "category": "Ultra-Light",
            "loader":   "pipeline",
        },
        {
            "hf_id":    "mlx-community/Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32",
            "category": "Ultra-Light",
            "loader":   "auto",
        },

        # ── Small  1B – 3B ─────────────────────────────────────────────────────
        {
            "hf_id":    "ibm-granite/granite-3.1-2b-instruct",
            "category": "Small",
            "loader":   "auto",
        },
        {
            "hf_id":    "iFaz/llama32_3B_en_emo_v1",
            "category": "Small",
            "loader":   "auto",
        },
        {
            "hf_id":    "DeepMount00/Qwen2-1.5B-Ita",
            "category": "Small",
            "loader":   "auto",
        },

        # ── Medium  3B – 7B ────────────────────────────────────────────────────
        {
            "hf_id":    "weathermanj/Menda-3B-500",
            "category": "Medium",
            "loader":   "auto",
        },
        {
            "hf_id":    "MaziyarPanahi/calme-2.1-phi3-4b",
            "category": "Medium",
            "loader":   "auto",
        },
        {
            "hf_id":    "MaziyarPanahi/calme-3.3-baguette-3b",
            "category": "Medium",
            "loader":   "auto",
        },

        # ── Large  7B – 9B ─────────────────────────────────────────────────────
        {
            "hf_id":    "ZeroXClem/Qwen2.5-7B-HomerAnvita-NerdMix",
            "category": "Large",
            "loader":   "auto",
        },
        {
            "hf_id":    "ibm-granite/granite-3.2-8b-instruct",
            "category": "Large",
            "loader":   "auto",
        },
        {
            "hf_id":    "Goekdeniz-Guelmez/josie-7b-v6.0-step2000",
            "category": "Large",
            "loader":   "auto",
        },

        # ── Ultra Large  9B – 12B ──────────────────────────────────────────────
        {
            "hf_id":    "recoilme/recoilme-gemma-2-9B-v0.3",
            "category": "Ultra Large",
            "loader":   "auto",
        },
        {
            "hf_id":    "princeton-nlp/gemma-2-9b-it-DPO",
            "category": "Ultra Large",
            "loader":   "auto",
        },
        {
            "hf_id":    "01-ai/Yi-1.5-9B-Chat",
            "category": "Ultra Large",
            "loader":   "auto",
        },
    ]

    print(f"Models registered: {len(MODEL_REGISTRY)}")
    for m in MODEL_REGISTRY:
        print(f"  [{m['category']:<12}]  {m['hf_id']}")



    # ============================================================
    # FLAT PROMPT LIST
    # Build a single list of (category, prompt_id, prompt_text)
    # tuples from ALL_PROMPTS — used for looping during benchmark.
    # ============================================================

    FLAT_PROMPTS = []
    for category, prompt_list in ALL_PROMPTS.items():
        for p in prompt_list:
            FLAT_PROMPTS.append({
                "prompt_type": category,
                "prompt_id":   p["id"],
                "prompt_text": p["prompt"],
            })

    print(f"Total flat prompts: {len(FLAT_PROMPTS)}")
    for fp in FLAT_PROMPTS:
        print(f"  [{fp['prompt_type']:<25}] {fp['prompt_id']}")





    # ============================================================
    # INFERENCE HELPERS
    #
    # run_with_auto()     — for models with a chat template
    #                       (mirrors ai_prototype.ipynb Qwen/Llama style)
    # run_with_pipeline() — for models loaded via transformers pipeline
    #                       (mirrors ai_prototype.ipynb JayHyeon style)
    # ============================================================

    MAX_NEW_TOKENS = 512


    def run_with_auto(model, tokenizer, prompt_text):
        """
        Runs a single prompt through an AutoModelForCausalLM model.
        Uses apply_chat_template when available (instruct models),
        falls back to plain tokenization (base models).

        Returns (generated_text, latency_seconds, tokens_per_second).
        """
        messages = [{"role": "user", "content": prompt_text}]

        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        else:
            model_inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

        input_len = model_inputs["input_ids"].shape[1]

        start = time.perf_counter()
        with torch.no_grad():
            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,           # greedy — deterministic & faster
                pad_token_id=tokenizer.eos_token_id,
            )
        latency = time.perf_counter() - start

        # Strip prompt tokens (same as ai_prototype.ipynb)
        new_ids = generated_ids[0][input_len:]
        tokens_generated = new_ids.shape[0]
        tok_per_sec = round(tokens_generated / latency, 2) if latency > 0 else 0.0

        generated_text = tokenizer.decode(new_ids, skip_special_tokens=True)
        return generated_text, round(latency, 2), tok_per_sec


    def run_with_pipeline(generator, prompt_text):
        """
        Runs a single prompt through a transformers pipeline.
        Mirrors the JayHyeon model block in ai_prototype.ipynb.

        Returns (generated_text, latency_seconds, tokens_per_second).
        """
        messages = [{"role": "user", "content": prompt_text}]

        start = time.perf_counter()
        output = generator(
            [messages],
            max_new_tokens=MAX_NEW_TOKENS,
            return_full_text=False
        )
        latency = time.perf_counter() - start

        generated_text = output[0][0]["generated_text"]

        # Approximate token count from word count (pipeline doesn't expose token ids)
        approx_tokens = len(generated_text.split())
        tok_per_sec = round(approx_tokens / latency, 2) if latency > 0 else 0.0

        return generated_text, round(latency, 2), tok_per_sec



    # ============================================================
    # MAIN BENCHMARK LOOP
    # Iterates: 15 models × 25 prompts = 375 inference calls.
    #
    # For each model:
    #   1. Load model (measure load time for reference)
    #   2. Run all 25 prompts one-by-one
    #   3. Record metrics
    #   4. Unload model + clear GPU cache
    # ============================================================

    results = []   # list of dicts — one per (model × prompt) row

    TOTAL_RUNS = len(MODEL_REGISTRY) * len(FLAT_PROMPTS)
    run_count  = 0

    print(f"Starting benchmark: {len(MODEL_REGISTRY)} models × {len(FLAT_PROMPTS)} prompts = {TOTAL_RUNS} runs\n")
    print("=" * 80)

    for model_meta in MODEL_REGISTRY[3:]:
        hf_id    = model_meta["hf_id"]
        category = model_meta["category"]
        loader   = model_meta["loader"]

        print(f"\n▶  Loading  [{category}]  {hf_id}")
        load_start = time.perf_counter()

        # ── Load model ──────────────────────────────────────────────────────────
        try:
            if loader == "auto":
                tokenizer = AutoTokenizer.from_pretrained(hf_id)
                model = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    torch_dtype="auto",
                    device_map="auto"
                )
                model.eval()
                generator = None
            else:  # pipeline
                generator = pipeline(
                    "text-generation",
                    model=hf_id,
                    device=0 if device == "cuda" else -1
                )
                tokenizer = None
                model     = None
        except Exception as e:
            print(f"  ✖ Failed to load {hf_id}: {e}")
            continue

        load_time = round(time.perf_counter() - load_start, 2)
        print(f"  ✔ Loaded in {load_time}s  |  running {len(FLAT_PROMPTS)} prompts...")

        # ── Run all 25 prompts ──────────────────────────────────────────────────
        for fp in FLAT_PROMPTS:
            run_count += 1
            progress = f"[{run_count}/{TOTAL_RUNS}]"

            try:
                if loader == "auto":
                    gen_text, latency, tok_sec = run_with_auto(
                        model, tokenizer, fp["prompt_text"]
                    )
                else:
                    gen_text, latency, tok_sec = run_with_pipeline(
                        generator, fp["prompt_text"]
                    )
            except Exception as e:
                print(f"    {progress} ERROR on {fp['prompt_id']}: {e}")
                gen_text = f"ERROR: {e}"
                latency  = -1
                tok_sec  = -1

            print(f"    {progress}  {fp['prompt_type']}/{fp['prompt_id']}  "
                f"latency={latency}s  tok/s={tok_sec}")

            results.append({
                "model":         hf_id,
                "model_category": category,
                "prompt_type":   fp["prompt_type"],
                "prompt_id":     fp["prompt_id"],
                "latency_s":     latency,
                "tok_per_sec":   tok_sec,
                "output":        gen_text,
                # ── Self-evaluation scores filled in manually in the next cell ──
                "instruction_adherence": None,
                "accuracy":              None,
                "completeness":          None,
                "structure":             None,
                "clarity":               None,
                "overall_score":         None,
            })

        # ── Unload model ────────────────────────────────────────────────────────
        del model
        del tokenizer
        del generator
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

        print(f"  ✔ Unloaded {hf_id}")
        
        if run_count >= 25 * 3:
            break

    print("\n" + "=" * 80)
    print(f"Benchmark complete. Total rows collected: {len(results)}")



    # ============================================================
    # SAVE RAW RESULTS TO CSV
    # Saved immediately after the loop so outputs are safe even if
    # the notebook kernel crashes during manual scoring.
    # ============================================================

    df = pd.DataFrame(results)

    CSV_PATH = "benchmark_results.csv"
    df.to_csv(CSV_PATH, index=False, mode="a", header=not pd.io.common.file_exists(CSV_PATH)) 

    print(f"Results saved to: {CSV_PATH}")
    print(f"Shape: {df.shape}  ({df.shape[0]} rows × {df.shape[1]} columns)")
    df.head()





    # ============================================================
    # PERFORMANCE SUMMARY TABLE
    # Mirrors the MODEL PERFORMANCE COMPARISON table from
    # section-3-week-7.ipynb.
    # ============================================================

    # Aggregate per model
    perf = (
        df[df["latency_s"] >= 0]  # exclude error rows
        .groupby(["model", "model_category"])
        .agg(
            avg_latency_s=("latency_s",  "mean"),
            avg_tok_per_sec=("tok_per_sec", "mean"),
            total_prompts=("prompt_id",  "count"),
        )
        .reset_index()
        .sort_values("model_category")
    )

    print("=" * 100)
    print("MODEL PERFORMANCE SUMMARY".center(100))
    print("=" * 100)
    header = f"{'Model':<55} {'Category':<13} {'Avg Latency(s)':>15} {'Avg Tok/s':>10} {'# Prompts':>10}"
    print(header)
    print("-" * 100)
    for _, row in perf.iterrows():
        print(
            f"{row['model']:<55} {row['model_category']:<13}"
            f"{row['avg_latency_s']:>15.2f} {row['avg_tok_per_sec']:>10.2f} {row['total_prompts']:>10}"
        )
    print("=" * 100)





    # ============================================================
    # GENERATION OUTPUT PREVIEW
    # Prints the first output for each model (prompt C1) so you
    # can quickly spot formatting / quality differences.
    # ============================================================

    preview = df[df["prompt_id"] == "C1"][["model", "model_category", "output"]]

    print("\n" + "=" * 80)
    print("GENERATION QUALITY PREVIEW — Prompt C1 (classification, paid subscription)".center(80))
    print("=" * 80)

    for _, row in preview.iterrows():
        print(f"\n[{row['model_category']}]  {row['model']}")
        print("-" * 80)
        print(str(row["output"])[:400])   # first 400 chars




    # ============================================================
    # BENCHMARK RESULTS TABLE
    # Final table matching the assignment format:
    #   Model | Category | Tok/s | Latency | Prompt Type | Prompt ID | Scores
    # ============================================================

    display_cols = [
        "model", "model_category", "tok_per_sec", "latency_s",
        "prompt_type", "prompt_id",
        "instruction_adherence", "accuracy", "completeness",
        "structure", "clarity", "overall_score"
    ]

    print("Full benchmark table (all 375 rows):")
    pd.set_option("display.max_rows", 400)
    pd.set_option("display.max_colwidth", 50)
    pd.set_option("display.width", 200)
    print(df[display_cols].to_string(index=False))



    # ============================================================
    # CHART: Average Tokens/sec per Model
    # Mirrors the scatter plot from section-3-week-7.ipynb.
    # ============================================================

    import matplotlib.pyplot as plt

    chart_data = (
        df[df["tok_per_sec"] > 0]
        .groupby("model")["tok_per_sec"]
        .mean()
        .reset_index()
    )

    # Short display names
    chart_data["short_name"] = chart_data["model"].apply(lambda x: x.split("/")[-1][:30])

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(chart_data["short_name"], chart_data["tok_per_sec"], color="steelblue")
    ax.set_xlabel("Average Tokens per Second")
    ax.set_title("Benchmark: Average Generation Speed per Model (all 25 prompts)")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig("benchmark_speed_chart.png", dpi=120)
    plt.show()
    print("Chart saved to benchmark_speed_chart.png")





if __name__ == "__main__":
    main()
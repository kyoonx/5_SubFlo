from datetime import timedelta, datetime
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, TemplateView
from subscriptions.models import Subscription, EmailMessage
from accounts.models import UserProfile
from django.db.models import Q, Sum, Count
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
from decimal import Decimal
import calendar
import random
import csv
from dateutil.relativedelta import relativedelta
import requests

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

############################################################
#################### Internal API Views ####################
############################################################

class SubscriptionList(LoginRequiredMixin, ListView):
    model = Subscription
    context_object_name = "subscriptions"
    template_name = "dashboard/subscription_list.html"
    redirect_field_name = 'next'
    

    def get_queryset(self):
        queryset = Subscription.objects.filter(user=self.request.user)
        q = self.request.GET.get("q", "").strip()
        platform_filter = self.request.GET.get("platform_filter")

        if q:
            queryset = queryset.filter(Q(platform_name__icontains=q) | Q(service_name__icontains=q) | Q(email_message_id__sender__icontains=q))

        if platform_filter == "trial":
            queryset = queryset.filter(is_trial=True)
        elif platform_filter == "expiring":
            today = timezone.now().date()
            queryset = queryset.filter(end_date__isnull=False, end_date__lte=today + timedelta(days=30))
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["platform_filter"] = self.request.GET.get("platform_filter")
        ctx["user_id"] = self.request.GET.get("user_id")

        today = timezone.now().date()
        # soon = today + timedelta(days=7)
        # current_month_start = today.replace(day=1)
        # current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        total_subscriptions = Subscription.objects.filter(user=self.request.user)
        total_active_subscriptions = total_subscriptions.filter(already_canceled=False).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        total_active_trial_subscriptions = total_active_subscriptions.filter(is_trial=True)

        # Monthly spend: sum of price for active, non-trial subscriptions
        monthly_spend_qs = total_active_subscriptions.filter(is_trial=False, price__isnull=False)
        ctx["monthly_spend"] = monthly_spend_qs.aggregate(total=Sum("price"))["total"] or Decimal("0.00")

        # Upcoming renewals: end_date in the next 30 days (active subs with end_date in range)
        soon_end = today + timedelta(days=30)
        upcoming_qs = Subscription.objects.filter(
            user=self.request.user,
            already_canceled=False,
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=soon_end,
        ).order_by("end_date")
        ctx["upcoming_renewals_count"] = upcoming_qs.count()

        # Group upcoming renewals by relative day (Tomorrow, In Two Days, ...) for sidebar
        day_labels = {
            0: "Today",
            1: "Tomorrow",
            2: "In Two Days",
            3: "In Three Days",
            4: "In Four Days",
            5: "In Five Days",
            6: "In Six Days",
            7: "In One Week",
        }
        upcoming_by_day = {}
        for sub in upcoming_qs:
            delta = (sub.end_date - today).days
            label = day_labels.get(delta, f"In {delta} Days" if delta <= 30 else None)
            if label and delta <= 30:
                upcoming_by_day.setdefault(label, []).append(sub)
        ctx["upcoming_renewals_grouped"] = [
            {"label": label, "subscriptions": subs}
            for label, subs in upcoming_by_day.items()
        ]
        # Sort by first subscription's end_date
        ctx["upcoming_renewals_grouped"].sort(
            key=lambda g: g["subscriptions"][0].end_date if g["subscriptions"] else today
        )

        ctx["total_subscriptions"] = total_subscriptions.count()
        ctx["total_active_subscriptions"] = total_active_subscriptions.count()
        ctx["total_active_trial_subscriptions"] = total_active_trial_subscriptions.count()

        # ── Monthly cost data for bar chart (first 6 months of current year) ──
        current_year = today.year
        subscriptions_per_month = (
            Subscription.objects
            .filter(user=self.request.user)
            .filter(already_canceled=False, is_trial=False, price__isnull=False)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total_cost=Sum('price'))
            .order_by('month')
        )
        monthly_costs = {}
        for month_num in range(1, 13):
            monthly_costs[month_num] = Decimal("0.00")
        for item in subscriptions_per_month:
            if item['month']:
                md = item['month'].date() if hasattr(item['month'], 'date') else item['month']
                if md.year == current_year:
                    monthly_costs[md.month] = item['total_cost'] or Decimal("0.00")

        all_values = [float(monthly_costs[m]) for m in range(1, 13)]
        if sum(all_values) == 0:
            base_costs = [168, 385, 201, 298, 187, 195, 291, 110, 215, 390, 280, 112]
            all_values = [max(0, c + random.randint(-20, 20)) for c in base_costs]

        bar_colors = [
            ("rgba(160,188,232,0.25)", "rgba(160,188,232,1)"),
            ("rgba(107,230,211,0.25)", "rgba(107,230,211,1)"),
            ("rgba(0,0,0,0.12)",       "rgba(0,0,0,0.7)"),
            ("rgba(125,187,255,0.25)", "rgba(125,187,255,1)"),
            ("rgba(184,153,235,0.25)", "rgba(184,153,235,1)"),
            ("rgba(113,221,140,0.25)", "rgba(113,221,140,1)"),
        ]

        chart_values = all_values[:6]
        chart_labels = [calendar.month_abbr[m] for m in range(1, 7)]
        max_val = max(chart_values) if chart_values and max(chart_values) > 0 else 1
        chart_months = []
        for i, (label, val) in enumerate(zip(chart_labels, chart_values)):
            bg_pct = (val / max_val) * 100
            fg_pct = max(0, bg_pct - 12.5)
            cb, cf = bar_colors[i % len(bar_colors)]
            chart_months.append({
                "label": label,
                "bg_height": round(bg_pct, 1),
                "fg_height": round(fg_pct, 1),
                "color_bg": cb,
                "color_fg": cf,
            })
        ctx["chart_months"] = chart_months

        nice_max = int(max_val)
        if nice_max < 10:
            nice_max = 10
        ctx["chart_y_labels"] = [str(nice_max), str(int(nice_max * 2 / 3)), str(int(nice_max / 3)), "0"]

        # Month-over-month change percent
        cur_idx = today.month - 1
        if cur_idx >= 1 and all_values[cur_idx - 1] != 0:
            pct = round((all_values[cur_idx] - all_values[cur_idx - 1]) / all_values[cur_idx - 1] * 100)
            ctx["monthly_spend_change_percent"] = pct
        else:
            ctx["monthly_spend_change_percent"] = None

        # ── Donut: Subscriptions by Category (placeholder categories) ──
        total_spend = float(ctx["monthly_spend"])
        circumference = 289.0
        cat_defs = [
            {"label": "Direct",    "pct": 53, "color": "#7dbbff"},
            {"label": "Affiliate", "pct": 24, "color": "#71dd8c"},
            {"label": "Sponsored", "pct": 14, "color": "#b899eb"},
            {"label": "E-mail",    "pct": 9,  "color": "#6be6d3"},
        ]
        offset = circumference / 4
        categories = []
        for cd in cat_defs:
            dash = (cd["pct"] / 100) * circumference
            categories.append({
                "label": cd["label"],
                "color": cd["color"],
                "dash_length": round(dash, 1),
                "dash_offset": round(offset, 1),
                "amount": Decimal(str(round(total_spend * cd["pct"] / 100, 2))),
            })
            offset -= dash
        ctx["categories"] = categories

        return ctx

    def post(self, request, *args, **kwargs):
        # Check if this is a create subscription form submission
        if request.POST.get('form_type') == 'create_subscription':

            # Required fields
            platform_name = request.POST.get('platform_name', '').strip()
            service_name = request.POST.get('service_name', '').strip()

            # Optional fields
            start_date_str = request.POST.get('start_date', '').strip()
            end_date_str = request.POST.get('end_date', '').strip()
            price_str = request.POST.get('price', '').strip()
            currency = request.POST.get('currency', 'USD').strip()
            payment_method = request.POST.get('payment_method', '').strip()
            unsubscribe_link = request.POST.get('unsubscribe_link', '').strip()
            notes = request.POST.get('notes', '').strip()

            # Checkboxes (important: unchecked = None)
            is_trial = request.POST.get('is_trial') == 'on'
            already_canceled = request.POST.get('already_canceled') == 'on'

            # Validate required fields (only platform_name & service_name are required in form)
            if platform_name and service_name:
                try:
                    # Price
                    price = Decimal(price_str) if price_str else None

                    # Dates
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

                    # Create subscription
                    Subscription.objects.create(
                        user=request.user,
                        platform_name=platform_name,
                        service_name=service_name,
                        start_date=start_date,
                        end_date=end_date,
                        is_trial=is_trial,
                        already_canceled=already_canceled,
                        price=price,
                        currency=currency or "USD",
                        payment_method=payment_method or None,
                        unsubscribe_link=unsubscribe_link or None,
                        notes=notes or None,
                    )

                    # Redirect to avoid resubmission on refresh
                    return redirect('subscription-list-url')

                except (ValueError, TypeError):
                    pass

        # If form submission was not create_subscription, just redirect to GET
        return redirect('subscription-list-url')


@login_required(login_url='login_urlpattern')
def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    return render(request, "dashboard/subscription_detail.html", {"subscription": subscription})


@login_required(login_url='login_urlpattern')
def subscription_edit(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        subscription.platform_name = request.POST.get('platform_name', '').strip() or subscription.platform_name
        subscription.service_name = request.POST.get('service_name', '').strip() or subscription.service_name
        subscription.currency = request.POST.get('currency', 'USD').strip() or 'USD'
        subscription.payment_method = request.POST.get('payment_method', '').strip() or None
        subscription.unsubscribe_link = request.POST.get('unsubscribe_link', '').strip() or None
        subscription.notes = request.POST.get('notes', '').strip() or None
        subscription.is_trial = request.POST.get('is_trial') == 'on'
        subscription.already_canceled = request.POST.get('already_canceled') == 'on'
        price_str = request.POST.get('price', '').strip()
        start_date_str = request.POST.get('start_date', '').strip()
        end_date_str = request.POST.get('end_date', '').strip()
        try:
            subscription.price = Decimal(price_str) if price_str else None
            subscription.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            subscription.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            subscription.save()
        except (ValueError, TypeError):
            pass
        return redirect('subscription-detail-url', pk=pk)
    return redirect('subscription-detail-url', pk=pk)


@login_required(login_url='login_urlpattern')
def subscription_delete(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        subscription.delete()
        return redirect('subscription-list-url')
    return redirect('subscription-detail-url', pk=pk)

@login_required(login_url='login_urlpattern')
def _subscription_export_queryset(request):
    """Ordered queryset for CSV/JSON export (model default ordering)."""
    return Subscription.objects.filter(user=request.user).order_by("user", "-end_date", "-start_date", "platform_name", "service_name")


@login_required(login_url='login_urlpattern')
def subscription_export_csv(request):
    """Return downloadable CSV of all subscriptions."""
    queryset = _subscription_export_queryset(request)
    buffer = StringIO()
    writer = csv.writer(buffer)
    headers = [
        "id", "user", "platform_name", "service_name", "start_date", "end_date",
        "is_trial", "already_canceled", "price", "currency", "payment_method",
        "notes", "created_at", "updated_at",
    ]
    writer.writerow(headers)
    for sub in queryset:
        row = [
            str(sub.id),
            sub.user.username if sub.user_id else "",
            sub.platform_name or "",
            sub.service_name or "",
            sub.start_date.isoformat() if sub.start_date else "",
            sub.end_date.isoformat() if sub.end_date else "",
            sub.is_trial,
            sub.already_canceled,
            str(sub.price) if sub.price is not None else "",
            sub.currency or "",
            sub.payment_method or "",
            (sub.notes or "").replace("\r", " ").replace("\n", " "),
            sub.created_at.isoformat() if sub.created_at else "",
            sub.updated_at.isoformat() if sub.updated_at else "",
        ]
        writer.writerow(row)
    filename = f"subscriptions_{timezone.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    response = HttpResponse("\ufeff" + buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url='login_urlpattern')
def subscription_export_json(request):
    """Return downloadable JSON of all subscriptions with metadata."""
    queryset = _subscription_export_queryset(request)
    rows = []
    for sub in queryset:
        rows.append({
            "id": str(sub.id),
            "user": sub.user.username if sub.user_id else "",
            "platform_name": sub.platform_name or "",
            "service_name": sub.service_name or "",
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "is_trial": sub.is_trial,
            "already_canceled": sub.already_canceled,
            "price": str(sub.price) if sub.price is not None else None,
            "currency": sub.currency or "",
            "payment_method": sub.payment_method or "",
            "notes": sub.notes or "",
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
        })
    payload = {
        "generated_at": timezone.now().isoformat(),
        "record_count": len(rows),
        "subscriptions": rows,
    }
    filename = f"subscriptions_{timezone.now().strftime('%Y-%m-%d_%H-%M')}.json"
    response = JsonResponse(payload, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

@login_required(login_url='login_urlpattern')
def reports_view(request):
    """Reports page: grouped summaries and totals, with CSV/JSON export links."""
    today = timezone.now().date()
    subscriptions_per_platform = (
        Subscription.objects.filter(user=request.user).values("platform_name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total_all = Subscription.objects.filter(user=request.user).count()
    total_active = Subscription.objects.filter(user=request.user, already_canceled=False).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).count()
    total_trial = Subscription.objects.filter(user=request.user, already_canceled=False, is_trial=True).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).count()
    total_canceled = Subscription.objects.filter(user=request.user, already_canceled=True).count()
    by_status = [
        {"status": "Active", "count": total_active},
        {"status": "Trial (active)", "count": total_trial},
        {"status": "Canceled", "count": total_canceled},
        {"status": "All", "count": total_all},
    ]
    context = {
        "subscriptions_per_platform": subscriptions_per_platform,
        "by_status": by_status,
        "total_subscriptions": total_all,
        "total_active_subscriptions": total_active,
        "total_active_trial_subscriptions": total_trial,
    }
    return render(request, "dashboard/reports.html", context)

@login_required(login_url='login_urlpattern')
def email_message_detail(request, pk):
    email_message = get_object_or_404(EmailMessage, pk=pk, user=request.user)
    template = loader.get_template("dashboard/email_message_detail.html")
    context = {"email_message": email_message}
    output = template.render(context, request)
    return HttpResponse(output)


@login_required(login_url='login_urlpattern')
def email_message_list(request):
    email_messages = EmailMessage.objects.filter(user=request.user).values("id", "subject", "sender", "received_date")
    template = loader.get_template("dashboard/email_message_list.html")
    context = {"email_messages": email_messages}
    output = template.render(context, request)
    return HttpResponse(output)



############################################################
#################### External API Views ####################
############################################################

@login_required(login_url='login_urlpattern')
def subscription_chart(request):
    """
    Generate a chart showing subscription distribution by platform.
    Returns PNG image via HttpResponse using BytesIO for memory efficiency.
    """
    # Data Aggregation using ORM
    platform_data = (
        Subscription.objects
        .filter(already_canceled=False)
        .values('platform_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Extract data for chart
    platforms = [item['platform_name'] for item in platform_data]
    counts = [item['count'] for item in platform_data]
    
    # Create the chart
    plt.figure(figsize=(10, 6))
    plt.bar(platforms, counts, color=['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe'])
    plt.title('Subscription Distribution by Platform', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Platform', fontsize=12)
    plt.ylabel('Number of Subscriptions', fontsize=12)
    plt.legend(['Subscriptions'], loc='upper right')
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    
    # Save to BytesIO (memory efficient)
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    plt.close()  # Close figure to free memory
    
    # Return PNG image
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required(login_url='login_urlpattern')
def subscriptions_per_month_chart(request):
    """
    Generate a bar chart showing total number of subscriptions per month.
    Returns PNG image via HttpResponse using BytesIO for memory efficiency.
    """
    
    # Get subscriptions per month for current year
    today = timezone.now().date()
    current_year = today.year
    
    subscriptions_per_month = (
        Subscription.objects
        .filter(already_canceled=False)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    # Create a dictionary with all 12 months
    monthly_data = {}
    month_names = []
    for month_num in range(1, 13):
        month_name = calendar.month_abbr[month_num]
        month_names.append(month_name)
        monthly_data[month_num] = 0
    
    # Fill in actual data
    for item in subscriptions_per_month:
        if item['month']:
            month_date = item['month'].date()
            if month_date.year == current_year:
                monthly_data[month_date.month] = item['count']
    
    # Generate test data if no data exists (for demonstration)
    total_count = sum(monthly_data.values())
    if total_count == 0:
        # Generate realistic test data based on the image
        base_counts = [160, 370, 200, 290, 180, 170, 280, 80, 190, 380, 280, 100]
        # Add some randomness
        counts = [max(0, int(count + random.randint(-20, 20))) for count in base_counts]
    else:
        # Use actual data, but ensure we have data for all months
        counts = [monthly_data[month_num] if monthly_data[month_num] > 0 else 0 for month_num in range(1, 13)]
        # If we have some data but not all months, fill in with small values
        if sum(counts) > 0:
            for i in range(12):
                if counts[i] == 0:
                    counts[i] = random.randint(10, 50)
    
    # Create the chart
    plt.figure(figsize=(12, 6))
    plt.bar(month_names, counts, color='#465fff', width=0.6)
    plt.title('Total Subscriptions per Month', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Month', fontsize=12)
    plt.ylabel('Number of Subscriptions', fontsize=12)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    
    # Save to BytesIO (memory efficient)
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    plt.close()  # Close figure to free memory
    
    # Return PNG image
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required(login_url='login_urlpattern')
def api_all_active_subscriptions(request):
    """
    GET /api/subscriptions/active
    """
    user = request.user

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found"}, status=404)

    today = timezone.now().date()

    fields = [
        field.name
        for field in Subscription._meta.fields
        if field.name != "user"
    ]
    
    rows = Subscription.objects.filter(
        user=profile.user,
        already_canceled=False
    ).filter(
        Q(end_date__isnull=True) |
        Q(end_date__gte=today)
    ).values(*fields)

    data = list(rows)
    return JsonResponse({"user_id": profile.id, "num_active_subscriptions": len(data), "subscriptions": data})


@login_required(login_url='login_urlpattern')
def api_cost_per_month(request):
    """
    Return the summary of total subscription costs per month for the past 12 months for a given user.
    
    GET /api/subscriptions/cost_per_month/
    
    Response Format:
        {
            "user_id": <profile_uuid>,
            "monthly_costs": {
                "2025-03": 24.99,
                "2025-04": 11.45,
                "2025-05": 20.00,
                "2025-06": 20.00,
                "2025-07": 20.00,
                "2025-08": 10.99,
                "2025-09": 10.99,
                "2025-10": 11.49,
                "2025-11": 12.49,
                "2025-12": 19.99,
                "2026-01": 24.99,
                "2026-02": 17.98
            }
        }
        
    Where today is in February 2026, so we return costs for the past 12 months including current month (2025-03 to 2026-02).
    """
    user = request.user
    
    if not user:
        return JsonResponse({"error": "Not authenticated"}, status=400)

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found"}, status=404)

    today = timezone.now().date()
    start_period = (today.replace(day=1) - relativedelta(months=11))  # 12 months including current month
    end_period = today.replace(day=1)

    subscriptions_per_month = (
        Subscription.objects
        .filter(user=profile.user, is_trial=False, price__isnull=False)
        .annotate(month=TruncMonth('start_date'))
        .values('month')
        .annotate(total_cost=Sum('price'))
        .order_by('month')
    )


    monthly_costs = {}
    current = start_period
    for _ in range(12):
        monthly_costs[current] = Decimal("0.00")
        current += relativedelta(months=1)

    for item in subscriptions_per_month:
        if item['month']:
            month_date = item['month']
            if start_period <= month_date <= end_period:
                monthly_costs[month_date] = item['total_cost'] or Decimal("0.00")

    response_data = {
        'user_id': profile.id,
        'monthly_costs': {
            month.strftime("%Y-%m"): float(cost)
            for month, cost in monthly_costs.items()
        }
    }
    
    return JsonResponse(response_data)



class VegaLiteBarAPI(TemplateView):
    template_name = "dashboard/vega-lite-bar-cost_per_month.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.GET.get("user_id")
        context["user_id"] = user_id
        return context
    
class VegaLiteLineAPI(TemplateView):
    template_name = "dashboard/vega-lite-line-cost_per_month.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.GET.get("user_id")
        context["user_id"] = user_id
        return context
    
def currency_convert(request):
    """
    GET /dashboard/api/currency-convert/?q=EUR
    Fetches live USD exchange rate from Frankfurter API (no key needed),
    then combines it with internal Subscription data to return each
    subscription's cost converted to the requested currency.
    """
    target_currency = request.GET.get("q", "").strip().upper()

    if not target_currency:
        return JsonResponse(
            {"error": "Missing query parameter. Usage: ?q=EUR"},
            status=400
        )

    # --- 1. External API call ---
    try:
        response = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": target_currency},
            timeout=5,
        )
        response.raise_for_status()
        rate_data = response.json()
    except requests.exceptions.Timeout:
        return JsonResponse({"error": "Exchange rate API timed out."}, status=504)
    except requests.exceptions.HTTPError as e:
        return JsonResponse({"error": f"Exchange rate API error: {str(e)}"}, status=400)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Could not reach exchange rate API: {str(e)}"}, status=502)

    rate = rate_data.get("rates", {}).get(target_currency)
    if rate is None:
        return JsonResponse(
            {"error": f"Currency '{target_currency}' not supported. Try EUR, GBP, JPY, CAD, etc."},
            status=400,
        )

    # --- 2. Combine with internal Subscription data ---
    today = timezone.now().date()
    active_subs = Subscription.objects.filter(
        already_canceled=False,
        price__isnull=False,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    )

    # --- 3. Apply processing: convert each price, compute totals ---
    converted_subs = []
    total_usd = Decimal("0.00")
    total_converted = Decimal("0.00")
    trial_count = 0

    for sub in active_subs:
        price_usd = sub.price
        price_converted = round(price_usd * Decimal(str(rate)), 2)
        total_usd += price_usd
        total_converted += price_converted
        if sub.is_trial:
            trial_count += 1

        converted_subs.append({
            "platform": sub.platform_name,
            "service": sub.service_name,
            "is_trial": sub.is_trial,
            "renewal_date": str(sub.end_date) if sub.end_date else None,
            "price_usd": float(price_usd),
            f"price_{target_currency.lower()}": float(price_converted),
        })

    return JsonResponse({
        "exchange_rate": {
            "from": "USD",
            "to": target_currency,
            "rate": rate,
            "date": rate_data.get("date"),
        },
        "summary": {
            "total_monthly_usd": float(round(total_usd, 2)),
            f"total_monthly_{target_currency.lower()}": float(round(total_converted, 2)),
            "active_subscription_count": len(converted_subs),
            "active_trial_count": trial_count,
        },
        "subscriptions": converted_subs,
    })
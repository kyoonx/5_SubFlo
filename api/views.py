from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count
from subscriptions.models import Subscription


@require_GET
def top_subscriptions_by_platform(request):
    """
    GET /api/subscriptions/top-by-platform/
    Returns the top 3 platforms by subscription count.
    """
    top_platforms = (
        Subscription.objects
        .values('platform_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:3]
    )
    data = [
        {"platform_name": p['platform_name'], "subscription_count": p['count']}
        for p in top_platforms
    ]
    return JsonResponse({"top_platforms": data})
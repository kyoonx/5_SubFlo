from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import ListView
from subscriptions.models import Subscription


def subscription_list(request):
    subscriptions = Subscription.objects.all()
    template = loader.get_template("dashboard/subscription_list.html")
    context = {"subscriptions": subscriptions}
    output = template.render(context, request)
    return HttpResponse(output)

def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    return render(request, "dashboard/subscription_detail.html", {"subscription": subscription})
    


# View 1 (FBV): HttpResponse
def subscriptions_manual_html(request):
    """
    Returns raw HTML directly via HttpResponse.
    """
    subs = Subscription.objects.all()[:10]  # keep it simple for screenshot
    items = "".join(
        f"<li><b>{getattr(s, 'name', 'Subscription')}</b> — "
        f"{getattr(s, 'platform', '')} "
        f"</li>"
        for s in subs
    )

    html = f"""
    <html>
      <body style="font-family: Arial;">
        <h1>SubFlo — Subscriptions (Manual HttpResponse)</h1>
        <p>Showing up to 10 subscriptions.</p>
        <ul>{items or "<li>No subscriptions found.</li>"}</ul>
      </body>
    </html>
    """
    return HttpResponse(html)


# View 2 (FBV): render() shortcut
def subscriptions_render(request):
    """
    Queries subscriptions and renders a template with context.
    """
    subs = Subscription.objects.all()
    context = {"subscriptions": subs}
    return render(request, "dashboard/subscriptions_render.html", context)


# View 3 (CBV): Base CBV (inherit from View)
class SubscriptionsBaseCBV(View):
    """
    Base CBV that manually queries and renders.
    """
    def get(self, request):
        subs = Subscription.objects.all()
        context = {"subscriptions": subs}
        return render(request, "dashboard/subscriptions_base_cbv.html", context)


# View 4 (CBV): Generic CBV (ListView)
class SubscriptionsGenericListView(ListView):
    model = Subscription
    template_name = "dashboard/subscriptions_generic_list.html"
    context_object_name = "subscriptions"

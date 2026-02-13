from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from subscriptions.models import Subscription, EmailMessage
from django.db.models import Q, Sum


class SubscriptionList(ListView):
    model = Subscription
    context_object_name = "subscriptions"
    template_name = "dashboard/subscription_list.html"

    def get_queryset(self):
        queryset = Subscription.objects.all()
        q = self.request.GET.get("q", "").strip()
        text = self.request.POST.get("text", "").strip()

        if q:
            queryset = queryset.filter(Q(platform_name__icontains=q) | Q(service_name__icontains=q) | Q(email_message_id__sender__icontains=q))
        if text:
            queryset = queryset.filter(notes__icontains=text)

        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["text"] = self.request.POST.get("text", "").strip()
        
        ctx["total_subscriptions"] = Subscription.objects.count()
        ctx["total_trial_subscriptions"] = Subscription.objects.filter(is_trial=True).count()
        ctx["total_active_subscriptions"] = Subscription.objects.filter(already_canceled=False).count()
        
        today = timezone.now().date()
        soon = today + timedelta(days=7)

        ctx["total_soon_to_expire_subscriptions"] = (
            Subscription.objects.filter(
                user=self.request.user,
                already_canceled=False,
                end_date__gte=today,
                end_date__lte=soon,
            ).count()
        )
        
        # Credit/Debit card, PayPal, etc.
        ctx["total_cost_per_payment_method"] = (
            Subscription.objects.
            values("payment_method")
            .annotate(total_cost=Sum("price"))
        )

        
        return ctx

    def post(self, request, *args, **kwargs):
        text = request.POST.get("text", "").strip()
        q = self.request.GET.get("q", "").strip()

        queryset = Subscription.objects.all()
        if q:
            queryset = queryset.filter(Q(platform_name__icontains=q) | Q(service_name__icontains=q) | Q(email_message_id__sender__icontains=q))
        if text:
            queryset = queryset.filter(notes__icontains=text)
        
        subscriptions = list(queryset)
        context = {
            'subscriptions': subscriptions,
            'q': q,
            'text': text
        }
        return render(request, self.template_name, context)

def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    return render(request, "dashboard/subscription_detail.html", {"subscription": subscription})
    
def email_message_detail(request, pk):
    email_message = get_object_or_404(EmailMessage, pk=pk)
    template = loader.get_template("dashboard/email_message_detail.html")
    context = {"email_message": email_message}
    output = template.render(context, request)
    return HttpResponse(output)
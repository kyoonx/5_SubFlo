from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from subscriptions.models import Subscription, EmailMessage

class SubscriptionList(ListView):
    model = Subscription
    context_object_name = "subscriptions"
    template_name = "dashboard/subscription_list.html"

def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    return render(request, "dashboard/subscription_detail.html", {"subscription": subscription})
    
def email_message_detail(request, pk):
    email_message = get_object_or_404(EmailMessage, pk=pk)
    template = loader.get_template("dashboard/email_message_detail.html")
    context = {"email_message": email_message}
    output = template.render(context, request)
    return HttpResponse(output)
from django.urls import path
from dashboard.views import (
    EmailMessageDeleteView,
    SubscriptionList,
    VegaLiteBarAPI,
    VegaLiteLineAPI,
    api_all_active_subscriptions,
    api_cost_per_month,
    currency_convert,
    email_message_list,
    subscription_detail,
    subscription_edit,
    subscription_delete,
    email_message_detail,
    subscription_chart,
    subscriptions_per_month_chart,
    subscription_export_csv,
    subscription_export_json,
    reports_view,
)

urlpatterns = [
    path("", SubscriptionList.as_view(), name="subscription-list-url"),  
    
    path("<uuid:pk>", subscription_detail, name="subscription-detail-url"),
    path("<uuid:pk>/edit/", subscription_edit, name="subscription-edit-url"),
    path("<uuid:pk>/delete/", subscription_delete, name="subscription-delete-url"),
    
    path("subscriptions/export/csv/", subscription_export_csv, name="subscription-export-csv-url"),
    path("subscriptions/export/json/", subscription_export_json, name="subscription-export-json-url"),
    path("reports/", reports_view, name="reports-url"),
    
    path("email_message/", email_message_list, name="email_message_list-url"),
    path("email_message/<uuid:pk>", email_message_detail, name="email_message_detail-url"),
    
    path("email_message/<uuid:pk>/delete/", EmailMessageDeleteView.as_view(), name='email_message_delete-url'),
    
    path("api/subscriptions/active/", api_all_active_subscriptions, name="api-active-subscriptions-url"),
    path("api/subscriptions/cost_per_month/", api_cost_per_month, name="api-cost-per-month-url"),
    
    path("subscriptions/chart.png", subscription_chart, name="subscription-chart-url"),
    path("subscriptions/monthly-chart.png", subscriptions_per_month_chart, name="subscriptions-monthly-chart-url"),
    
    path("bar-charts/vega-lite/", VegaLiteBarAPI.as_view(), name="bar-chart-vega-lite"),
    path("line-charts/vega-lite/", VegaLiteLineAPI.as_view(), name="line-chart-vega-lite"),
    
    path("api/currency-convert/", currency_convert, name="currency-convert-url"),
    
]

from django.urls import path
from accounts.views import AccountDetail

urlpatterns = [
    path("<int:pk>", AccountDetail.as_view(), name="account-detail-url"),
]
from django.urls import path
from accounts.views import AccountDetail, api_verify_user_id

urlpatterns = [
    path("<uuid:pk>", AccountDetail.as_view(), name="account-detail-url"),
    path("api/accounts/verify/", api_verify_user_id, name="api-verify-user-id-url"),
]
from django.shortcuts import render, get_object_or_404
from django.views import View
from accounts.models import UserProfile

# Create your views here.
class AccountDetail(View):

    def get(self, request, pk):
        user_detail = get_object_or_404(UserProfile, pk=pk)
        
        return render(
            request,                                           
            'accounts/user_detail.html',
            {
                'user_detail': user_detail,
            },
        )


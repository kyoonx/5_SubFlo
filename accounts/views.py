from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
from accounts.models import UserProfile
# from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin


############################################################
#################### Internal API Views ####################
############################################################


# Create your views here.
class AccountDetail(LoginRequiredMixin, View):

    def get(self, request):
        user_detail = get_object_or_404(UserProfile, user=request.user)
        
        return render(
            request,                                           
            'accounts/user_detail.html',
            {
                'user_detail': user_detail,
            },
        )



############################################################
#################### External API Views ####################
############################################################

def api_verify_user_id(request):
    """
    GET /api/accounts/verify/?user_id=<profile_uuid>
    """
    profile_uuid = request.GET.get("user_id")
    
    if not profile_uuid:
        return HttpResponse("No user_id provided.", status=400)

    try:
        _ = UserProfile.objects.select_related("user").get(id=profile_uuid)
        return HttpResponse(f"This user_id ({profile_uuid}) is existing/valid.", status=200)
    except UserProfile.DoesNotExist:
        return HttpResponse(f"This user_id ({profile_uuid}) does not exist.", status=404)
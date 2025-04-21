from django.contrib.auth.models import User
from django.http import JsonResponse


def account_username_validation(request):
    """Used for validate account username during signup"""
    username = request.GET.get("username")
    data = {"username_exists": User.objects.filter(username=username).exists()}

    return JsonResponse(data)

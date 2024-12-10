def auth_context(request):
    return {
        'user': request.user,
    }
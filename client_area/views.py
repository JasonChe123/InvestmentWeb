from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
from .forms import ProfileForm


@login_required
def home(request):
    return render(request, "client_area/index.html")

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Save profile with picture first
            profile = form.save()
            
            # Update user info
            user = request.user
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('client_profile')
        else:
            messages.error(request, 'Error updating profile. Please check the form.')

    return render(request, "client_area/client_profile.html", {
        'profile': profile,
        'user': request.user
    })

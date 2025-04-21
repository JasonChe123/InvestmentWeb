from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, UpdateView
from long_short_strategy.models import LongShortEquity, StrategiesList
from .models import Profile
from .forms import ProfileForm


@login_required
def home(request):
    context = {"disable_animation": True}
    
    return render(request, "client_area/index.html", context)


@method_decorator(login_required, name="dispatch")
class ClientProfile(ListView):
    model = Profile
    template_name = "client_area/client_profile.html"

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Update context
        context["disable_animation"] = True
        context["form"] = ProfileForm()
        context["form"].fields.pop("profile_picture")

        # Disable inputs
        context["form"].fields["first_name"].disabled = True
        context["form"].fields["last_name"].disabled = True
        context["form"].fields["nick_name"].disabled = True

        # Setup default value
        res = Profile.objects.get(user=self.request.user)
        context["form"].fields["first_name"].initial = res.first_name
        context["form"].fields["last_name"].initial = res.last_name
        context["form"].fields["nick_name"].initial = res.nick_name

        return context


@method_decorator(login_required, name="dispatch")
class ClientProfileUpdate(UpdateView):
    model = Profile
    form_class = ProfileForm

    def get_queryset(self):
        return Profile.objects.filter(id=self.kwargs["pk"])

    def get_context_data(self):
        context = super().get_context_data(**self.kwargs)
        context["title"] = "Update Profile"
        context["disable_animation"] = True

        return context

    def get_success_url(self):
        return reverse("client_profile")


@method_decorator(login_required, name="dispatch")
class MyStrategiesListListView(ListView):
    model = StrategiesList
    template_name = "client_area/my_strategies_list.html"

    def get_queryset(self):
        return StrategiesList.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["disable_animation"] = True
        return context


@method_decorator(login_required, name="dispatch")
class MyStrategiesListView(ListView):
    model = LongShortEquity
    template_name = "client_area/my_strategies.html"
    fields = [
        "description",
    ]

    def get_queryset(self):
        return LongShortEquity.objects.filter(
            user=self.request.user, strategies_list__id=self.kwargs["pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["disable_animation"] = True
        context["strategies_list"] = StrategiesList.objects.get(id=self.kwargs["pk"])
        return context

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from long_short_strategy.models import LongShortEquity
from .models import Profile, StrategiesList
from .forms import ProfileForm, StrategiesListForm


@login_required
def home(request):
    context = {"disable_animation": True}

    return render(request, "client_area/index.html", context)


@method_decorator(login_required, name="dispatch")
class ProfileList(ListView):
    model = Profile
    template_name = "client_area/profile.html"

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
class ProfileUpdate(UpdateView):
    model = Profile
    form_class = ProfileForm

    def get_queryset(self):
        return Profile.objects.filter(id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Profile"
        context["disable_animation"] = True

        return context

    def get_success_url(self):
        return reverse("client_profile")


@method_decorator(login_required, name="dispatch")
class StrategiesListList(ListView):
    model = StrategiesList
    template_name = "client_area/strategies_list.html"

    def get_queryset(self):
        return StrategiesList.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["disable_animation"] = True
        return context


@method_decorator(login_required, name="dispatch")
class StrategiesListCreate(CreateView):
    model = StrategiesList
    form_class = StrategiesListForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["title"] = "Create New Strategy List"
        context["disable_animation"] = True
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("strategies_list")
    

@method_decorator(login_required, name="dispatch")
class StrategiesListUpdate(UpdateView):
    model = StrategiesList
    form_class = StrategiesListForm

    def get_queryset(self):
        return StrategiesList.objects.filter(id=self.kwargs["pk"])
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["title"] = "Edit Strategies List"
        context["disable_animation"] = True
        
        return context
    
    def get_success_url(self):
        return reverse("strategies_list")


@method_decorator(login_required, name="dispatch")
class StrategiesListDelete(DeleteView):
    model = StrategiesList

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["disable_animation"] = True
        return context
    
    def get_success_url(self):
        res = StrategiesList.objects.get(id=self.kwargs["pk"])
        messages.success(self.request, f"Strategies list '{res.title}' have been deleted.")
        return reverse_lazy("strategies_list")


@method_decorator(login_required, name="dispatch")
class MyStrategies(ListView):
    model = LongShortEquity
    template_name = "client_area/strategies_items.html"

    def get_queryset(self):
        return LongShortEquity.objects.filter(
            user=self.request.user, strategies_list__id=self.kwargs["pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "My Strategies"
        context["disable_animation"] = True
        context["strategies_list"] = StrategiesList.objects.get(id=self.kwargs["pk"])
        return context

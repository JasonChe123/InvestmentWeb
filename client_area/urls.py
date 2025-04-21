from django.urls import path
from .views import (
    home,
    # profile,
    ClientProfile,
    MyStrategiesListListView,
    MyStrategiesListView,
    ClientProfileUpdate,
)

urlpatterns = [
    path("", home, name="client_area"),
    path("profile", ClientProfile.as_view(), name="client_profile"),
    path(
        "update_profile/<int:pk>/",
        ClientProfileUpdate.as_view(),
        name="update_client_profile",
    ),
    path("strategies_list", MyStrategiesListListView.as_view(), name="strategies_list"),
    path(
        "my_strategies/<int:pk>/", MyStrategiesListView.as_view(), name="my_strategies"
    ),
]

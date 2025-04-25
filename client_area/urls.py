from django.urls import path
from .views import (
    home,
    ProfileList,
    ProfileUpdate,
    StrategiesListList,
    StrategiesListCreate,
    StrategiesListUpdate,
    StrategiesListDelete,
    MyStrategies,
)

urlpatterns = [
    path("", home, name="client_area"),
    path("profile", ProfileList.as_view(), name="client_profile"),
    path("update_profile/<int:pk>/", ProfileUpdate.as_view(), name="update_client_profile",),
    path("strategies_list/", StrategiesListList.as_view(), name="strategies_list"),
    path("strategies_list/create/", StrategiesListCreate.as_view(), name="strategies_list_create"),
    path("strategies_list/<int:pk>/update/", StrategiesListUpdate.as_view(), name="strategies_list_update"),
    path("strategies_list/<int:pk>/delete/", StrategiesListDelete.as_view(), name="strategies_list_delete"),
    path("my_strategies/<int:pk>/", MyStrategies.as_view(), name="my_strategies"),
]

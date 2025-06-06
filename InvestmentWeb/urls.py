"""
URL configuration for InvestmentWeb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontpage.urls')),
    path('accounts/', include('allauth.urls')),
    path('client_area/', include('client_area.urls')),
    path('strategy_pool/', include('strategy_pool.urls')),
    path('long_short/', include('long_short_strategy.urls')),
    # path('performance/', include('performance.urls')),
    # path('financial_weather/', include('financial_weather.urls')),
]

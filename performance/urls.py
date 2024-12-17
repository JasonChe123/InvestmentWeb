from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='performance'),
    path('add_portfolio', views.add_portfolio, name='add_portfolio'),
    path('check_portfolio_name', views.check_portfolio_name, name='check_portfolio_name'),
    path('save_portfolio', views.save_portfolio, name='save_portfolio'),
    path('edit_portfolio', views.edit_portfolio, name='edit_portfolio'),
    path('delete_portfolio', views.delete_portfolio, name='delete_portfolio'),
]

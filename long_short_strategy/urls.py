from django.urls import path
from . import views

urlpatterns = [
    path("backtest", views.BackTestView.as_view(), name="longshort-backtest"),
    path("search-method", views.search_method, name="search-method"),
    path(
        "update-stock-numbers", views.update_stock_numbers, name="update-stock-numbers"
    ),
    path("export-csv", views.export_csv, name="export-csv"),
    path("alter-my-strategy", views.alter_my_strategy, name="add-my-strategy"),
    path("strategies-list/add", views.add_strategies_list, name="add-strategies-list"),
]

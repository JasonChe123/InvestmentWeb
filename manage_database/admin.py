from advanced_filters.admin import AdminAdvancedFiltersMixin
from django.contrib import admin
from .models import CandleStick, Stock, IncomeStatement, BalanceSheet, CashFlow


class CandleStickAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ("stock__ticker", "date")
    list_display = ("stock__ticker", "date", "open", "close")
    advanced_filter_fields = ("stock__ticker", "date")


# Register your models here.
admin.site.register(CandleStick, CandleStickAdmin)
admin.site.register(Stock)
admin.site.register(IncomeStatement)
admin.site.register(BalanceSheet)
admin.site.register(CashFlow)

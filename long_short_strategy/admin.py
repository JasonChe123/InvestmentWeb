from django.contrib import admin
from .models import Stock, FinancialReport, BalanceSheet, CashFlow, CandleStick


admin.site.register(Stock)
admin.site.register(FinancialReport)
admin.site.register(BalanceSheet)
admin.site.register(CashFlow)
admin.site.register(CandleStick)
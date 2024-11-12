from django.db import models
import yfinance as yf


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    ipo_year = models.IntegerField(null=True)
    sector = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    market_cap = models.IntegerField(null=True)

    def __str__(self):
        return self.symbol


class FinancialReport(models.Model):
    symbol = models.OneToOneField(Stock, on_delete=models.CASCADE)

    Jan23 = models.JSONField(null=True)
    Feb23 = models.JSONField(null=True)
    Mar23 = models.JSONField(null=True)
    Apr23 = models.JSONField(null=True)
    May23 = models.JSONField(null=True)
    Jun23 = models.JSONField(null=True)
    Jul23 = models.JSONField(null=True)
    Aug23 = models.JSONField(null=True)
    Sep23 = models.JSONField(null=True)
    Oct23 = models.JSONField(null=True)
    Nov23 = models.JSONField(null=True)
    Dec23 = models.JSONField(null=True)

    Jan24 = models.JSONField(null=True)
    Feb24 = models.JSONField(null=True)
    Mar24 = models.JSONField(null=True)
    Apr24 = models.JSONField(null=True)
    May24 = models.JSONField(null=True)
    Jun24 = models.JSONField(null=True)
    Jul24 = models.JSONField(null=True)
    Aug24 = models.JSONField(null=True)
    Sep24 = models.JSONField(null=True)
    Oct24 = models.JSONField(null=True)
    Nov24 = models.JSONField(null=True)
    Dec24 = models.JSONField(null=True)


class BalanceSheet(models.Model):
    symbol = models.OneToOneField(Stock, on_delete=models.CASCADE)

    Jan23 = models.JSONField(null=True)
    Feb23 = models.JSONField(null=True)
    Mar23 = models.JSONField(null=True)
    Apr23 = models.JSONField(null=True)
    May23 = models.JSONField(null=True)
    Jun23 = models.JSONField(null=True)
    Jul23 = models.JSONField(null=True)
    Aug23 = models.JSONField(null=True)
    Sep23 = models.JSONField(null=True)
    Oct23 = models.JSONField(null=True)
    Nov23 = models.JSONField(null=True)
    Dec23 = models.JSONField(null=True)

    Jan24 = models.JSONField(null=True)
    Feb24 = models.JSONField(null=True)
    Mar24 = models.JSONField(null=True)
    Apr24 = models.JSONField(null=True)
    May24 = models.JSONField(null=True)
    Jun24 = models.JSONField(null=True)
    Jul24 = models.JSONField(null=True)
    Aug24 = models.JSONField(null=True)
    Sep24 = models.JSONField(null=True)
    Oct24 = models.JSONField(null=True)
    Nov24 = models.JSONField(null=True)
    Dec24 = models.JSONField(null=True)


class CashFlow(models.Model):
    symbol = models.OneToOneField(Stock, on_delete=models.CASCADE)

    Jan23 = models.JSONField(null=True)
    Feb23 = models.JSONField(null=True)
    Mar23 = models.JSONField(null=True)
    Apr23 = models.JSONField(null=True)
    May23 = models.JSONField(null=True)
    Jun23 = models.JSONField(null=True)
    Jul23 = models.JSONField(null=True)
    Aug23 = models.JSONField(null=True)
    Sep23 = models.JSONField(null=True)
    Oct23 = models.JSONField(null=True)
    Nov23 = models.JSONField(null=True)
    Dec23 = models.JSONField(null=True)

    Jan24 = models.JSONField(null=True)
    Feb24 = models.JSONField(null=True)
    Mar24 = models.JSONField(null=True)
    Apr24 = models.JSONField(null=True)
    May24 = models.JSONField(null=True)
    Jun24 = models.JSONField(null=True)
    Jul24 = models.JSONField(null=True)
    Aug24 = models.JSONField(null=True)
    Sep24 = models.JSONField(null=True)
    Oct24 = models.JSONField(null=True)
    Nov24 = models.JSONField(null=True)
    Dec24 = models.JSONField(null=True)


class IncomeStatement(models.Model):
    symbol = models.OneToOneField(Stock, on_delete=models.CASCADE)

    Jan23 = models.JSONField(null=True)
    Feb23 = models.JSONField(null=True)
    Mar23 = models.JSONField(null=True)
    Apr23 = models.JSONField(null=True)
    May23 = models.JSONField(null=True)
    Jun23 = models.JSONField(null=True)
    Jul23 = models.JSONField(null=True)
    Aug23 = models.JSONField(null=True)
    Sep23 = models.JSONField(null=True)
    Oct23 = models.JSONField(null=True)
    Nov23 = models.JSONField(null=True)
    Dec23 = models.JSONField(null=True)

    Jan24 = models.JSONField(null=True)
    Feb24 = models.JSONField(null=True)
    Mar24 = models.JSONField(null=True)
    Apr24 = models.JSONField(null=True)
    May24 = models.JSONField(null=True)
    Jun24 = models.JSONField(null=True)
    Jul24 = models.JSONField(null=True)
    Aug24 = models.JSONField(null=True)
    Sep24 = models.JSONField(null=True)
    Oct24 = models.JSONField(null=True)
    Nov24 = models.JSONField(null=True)
    Dec24 = models.JSONField(null=True)


class CandleStick(models.Model):
    symbol = models.OneToOneField(Stock, on_delete=models.CASCADE)

    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    adj_close = models.FloatField()
    volume = models.IntegerField()

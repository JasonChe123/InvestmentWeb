from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import ArrayField


class MyStrategy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategy')
    market_cap = ArrayField(models.CharField(max_length=20, null=True), size=6, null=True, blank=True)
    position_side_per_sector = models.IntegerField(null=False)
    min_stock_price = models.IntegerField(null=False)
    sort_ascending = models.BooleanField(null=False)
    sector = models.CharField(null=False, max_length=100)
    formula = models.CharField(null=False, max_length=500)

    def __str__(self):
        return f"{self.user}-{self.formula[:10]+'...' if len(self.formula) > 10 else self.formula}-{self.sector}"
    
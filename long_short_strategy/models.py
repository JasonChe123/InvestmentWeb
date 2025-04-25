from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from client_area.models import StrategiesList


class LongShortEquity(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="longshort_equity"
    )
    strategies_list = models.ForeignKey(
        StrategiesList,
        on_delete=models.CASCADE,
        related_name="longshort_equity",
    )
    created_on = models.DateField(auto_now_add=True)
    name = models.CharField(max_length=100, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    # Strategy's parameters
    market_cap = ArrayField(
        models.CharField(max_length=20, null=True), size=6, null=True, blank=True
    )
    position_side_per_sector = models.IntegerField(null=False)
    min_stock_price = models.IntegerField(null=False)
    sector = models.CharField(null=False, max_length=100)
    formula = models.CharField(null=False, max_length=500)
    sort_ascending = models.BooleanField(null=False)

    def clean(self):
        super().clean()
        if self.strategies_list.user != self.user:
            raise ValidationError("The strategies list must belong to the same user as the LongShortEquity instance.")
    
    def get_absolute_url(self):
        return reverse("my_strategies", args=[self.id])

    def __str__(self):
        return f"{self.name} - {self.strategies_list}"

    class Meta:
        ordering = ["name", "-created_on"]
        unique_together = [
            [
                "user",
                "strategies_list",
                "market_cap",
                "position_side_per_sector",
                "min_stock_price",
                "sector",
                "formula",
                "sort_ascending",
            ]
        ]
        verbose_name = "LongShort Equity"
        verbose_name_plural = "LongShort Equities"

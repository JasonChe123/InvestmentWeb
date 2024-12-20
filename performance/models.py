from django.db import models
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performance')
    group_name = models.CharField(max_length=100)
    financial_instrument = models.CharField(max_length=100)
    position = models.FloatField()
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_price = models.DecimalField(max_digits=10, decimal_places=2)
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'group_name', 'financial_instrument']

    def __str__(self):
        return f"{self.user.username} - {self.group_name} - {self.financial_instrument}"

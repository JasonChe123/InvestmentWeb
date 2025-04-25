from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    nick_name = models.CharField(max_length=50, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", null=True, blank=True
    )

    def __str__(self):
        return f"< {self.user.username} > Profile"


class StrategiesList(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="strategies_list"
    )
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, null=True, blank=True)
    created_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"< {self.user.username} > {self.title}"

    class Meta:
        ordering = ["user", "title"]
        unique_together = [["user", "title"]]
        verbose_name = "Strategies List"

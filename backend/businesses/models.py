from django.db import models
from django.contrib.auth.models import User


class BusinessProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    logo = models.ImageField(
        upload_to="business_logos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.company_name
"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.urls import path, include


def health_check(request):
    return JsonResponse({"status": "ok", "app": "InfluenceHub"})


def root_view(request):
    return JsonResponse({
        "status": "online",
        "app": "InfluenceHub API",
        "health": "/api/health/",
        "admin": "/admin/",
        "message": "InfluenceHub backend API is running. The frontend web application is hosted on Vercel."
    })


urlpatterns = [
    path("", root_view, name="root"),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),

    path("api/admin/", include("adminpanel.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("businesses.urls")),
    path("api/", include("campaigns.urls")),
    path("api/", include("influencers.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.urls import path

from .views import (
    BusinessDashboardView,
    BusinessRegisterView,
    BusinessProfileView,
)

urlpatterns = [
    path(
        "business/register/",
        BusinessRegisterView.as_view(),
        name="business-register",
    ),

    path(
        "business/profile/",
        BusinessProfileView.as_view(),
        name="business-profile",
    ),
    

    path(
        "business/dashboard/",
        BusinessDashboardView.as_view(),
    ),
]

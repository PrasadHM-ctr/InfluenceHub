from django.contrib import admin
from .models import EmailVerificationCode, UserRole

admin.site.register(UserRole)


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "consumed_at")
    search_fields = ("user__username", "user__email", "code")
    readonly_fields = ("created_at",)
from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "business", "influencer", "updated_at")
    search_fields = ("campaign__title", "business__company_name", "influencer__full_name")
    list_select_related = ("campaign", "business", "influencer")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("text", "sender__username")
    list_select_related = ("conversation", "sender")

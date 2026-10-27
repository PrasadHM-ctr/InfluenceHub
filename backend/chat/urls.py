from django.urls import path

from .views import (
    ConversationListView,
    ConversationMessagesView,
    StartConversationView,
    UnreadCountView,
    UploadMessageView,
)


urlpatterns = [
    path("chat/conversations/", ConversationListView.as_view(), name="chat-conversations"),
    path("chat/messages/<int:conversation_id>/", ConversationMessagesView.as_view(), name="chat-messages"),
    path("chat/start/", StartConversationView.as_view(), name="chat-start"),
    path("chat/upload/", UploadMessageView.as_view(), name="chat-upload"),
    path("chat/unread-count/", UnreadCountView.as_view(), name="chat-unread-count"),
]

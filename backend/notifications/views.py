from django.db.models import QuerySet
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


def notifications_for_user(user) -> QuerySet[Notification]:
    return Notification.objects.filter(recipient=user)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = notifications_for_user(request.user)
        unread_only = (request.query_params.get("unread_only") or "").lower() in {"1", "true", "yes"}
        if unread_only:
            queryset = queryset.filter(is_read=False)
        paginator = NotificationPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class NotificationUnreadCountView(APIView):
    """Lightweight badge count for the navbar bell."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"unread_count": notifications_for_user(request.user).filter(is_read=False).count()})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        updated = Notification.objects.filter(id=pk, recipient=request.user).update(is_read=True)
        if not updated:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Notification marked as read."})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = notifications_for_user(request.user).filter(is_read=False).update(is_read=True)
        return Response({"message": f"Marked {updated} notification(s) as read."})
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import ItemReport, ItemCategory, Claim, Notification, MessageThread, Message
from .serializers import (
    ItemReportSerializer, ItemCategorySerializer, 
    ClaimSerializer, NotificationSerializer
)


class ItemReportViewSet(viewsets.ModelViewSet):
    serializer_class = ItemReportSerializer
    queryset = ItemReport.objects.filter(is_approved=True)


class ItemCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ItemCategory.objects.all()
    serializer_class = ItemCategorySerializer


class ClaimViewSet(viewsets.ModelViewSet):
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]
    queryset = Claim.objects.all()
    
    def get_queryset(self):
        return self.queryset.filter(claimant=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class ReportSearchView(APIView):
    def get(self, request):
        # Placeholder implementation
        return Response({'results': []})


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, thread_id):
        # Placeholder implementation
        return Response({'messages': []})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notifications_read(request):
    """Mark notifications as read for the authenticated user."""
    try:
        data = request.data
        if data.get('mark_all'):
            # Mark all notifications as read for the current user
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        elif data.get('notification_id'):
            # Mark specific notification as read
            notification_id = data.get('notification_id')
            Notification.objects.filter(id=notification_id, user=request.user).update(is_read=True)
        
        return Response({'success': True})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_api(request, thread_id):
    return Response({'success': True})
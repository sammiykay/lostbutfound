from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'reports', api_views.ItemReportViewSet)
router.register(r'categories', api_views.ItemCategoryViewSet)
router.register(r'claims', api_views.ClaimViewSet)
router.register(r'notifications', api_views.NotificationViewSet)

urlpatterns = [
    # Custom API endpoints (must come before router URLs)
    path('auth/', include('rest_framework.urls')),
    path('reports/search/', api_views.ReportSearchView.as_view(), name='report_search'),
    path('notifications/mark-read/', api_views.mark_notifications_read, name='mark_notifications_read'),
    path('messages/<int:thread_id>/', api_views.MessageListView.as_view(), name='message_list_api'),
    path('messages/<int:thread_id>/send/', api_views.send_message_api, name='send_message_api'),
    
    # DRF Router URLs (must come after custom URLs)
    path('', include(router.urls)),
]
from django.urls import path
from . import views

app_name = 'lost_found'

urlpatterns = [
    # Home and main pages
    path('', views.HomeView.as_view(), name='home'),
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/new/', views.ReportCreateView.as_view(), name='report_create'),
    
    # Report management (specific patterns must come before general ones)
    path('reports/<int:pk>/edit/', views.ReportUpdateView.as_view(), name='report_update'),
    path('reports/<int:pk>/delete/', views.ReportDeleteView.as_view(), name='report_delete'),
    path('reports/<int:pk>/status/', views.update_report_status, name='update_report_status'),
    path('reports/<int:pk>/claim/', views.ClaimCreateView.as_view(), name='claim_create'),
    path('reports/<int:pk>/qr/', views.generate_qr_code, name='generate_qr'),
    path('reports/<int:pk>/success/', views.ReportSuccessView.as_view(), name='report_success'),
    
    # Report detail (general patterns must come after specific ones)
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('reports/<int:pk>/<slug:slug>/', views.ReportDetailView.as_view(), name='report_detail_slug'),
    
    # User dashboard and claims
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('claims/', views.ClaimListView.as_view(), name='claim_list'),
    path('claims/<int:pk>/', views.ClaimDetailView.as_view(), name='claim_detail'),
    path('claims/<int:pk>/approve/', views.approve_claim, name='approve_claim'),
    path('claims/<int:pk>/reject/', views.reject_claim, name='reject_claim'),
    path('claims/<int:pk>/collect/', views.mark_as_collected, name='mark_collected'),
    
    # Messaging
    path('messages/', views.MessageThreadListView.as_view(), name='message_list'),
    path('messages/<int:pk>/', views.MessageThreadDetailView.as_view(), name='message_detail'),
    path('messages/send/', views.send_message, name='send_message'),
    
    # Authentication
    path('accounts/register/', views.RegisterView.as_view(), name='register'),
    path('accounts/profile/', views.ProfileView.as_view(), name='profile'),
    path('accounts/profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    
    # QR codes
    path('qr/<str:code>/', views.QRTagView.as_view(), name='qr_tag'),
    
    # Static pages
    path('about/', views.StaticPageView.as_view(), {'slug': 'about'}, name='about'),
    path('privacy/', views.StaticPageView.as_view(), {'slug': 'privacy'}, name='privacy'),
    path('terms/', views.StaticPageView.as_view(), {'slug': 'terms'}, name='terms'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    
    # Admin dashboard
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-dashboard/reports/', views.AdminReportListView.as_view(), name='admin_report_list'),
    path('admin-dashboard/analytics/', views.AnalyticsView.as_view(), name='analytics'),
    
    # Admin report management
    path('admin-dashboard/reports/<int:pk>/', views.admin_report_detail, name='admin_report_detail'),
    path('admin-dashboard/reports/<int:pk>/approve/', views.approve_report, name='admin_approve_report'),
    path('admin-dashboard/reports/<int:pk>/reject/', views.reject_report, name='admin_reject_report'),
    path('admin-dashboard/reports/<int:pk>/flag/', views.flag_report, name='admin_flag_report'),
    path('admin-dashboard/reports/<int:pk>/unflag/', views.unflag_report, name='admin_unflag_report'),
    
    # Admin API endpoints
    path('api/admin/counts/', views.admin_counts_api, name='admin_counts_api'),
    
    # Notification API endpoints
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),

    path('accounts/logout/', views.logout_view, name='logout'),
]


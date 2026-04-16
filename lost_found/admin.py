from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import (
    UserProfile, ItemCategory, ItemReport, ItemPhoto, Claim,
    MessageThread, Message, Notification, AuditLog, FAQ, 
    StaticPage, SiteSetting, QRTag
)
import csv
from django.http import HttpResponse
from datetime import datetime


class ItemPhotoInline(admin.TabularInline):
    model = ItemPhoto
    extra = 0
    fields = ['image', 'caption', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 0
    fields = ['claimant', 'status', 'created_at', 'message']
    readonly_fields = ['claimant', 'created_at', 'message']
    can_delete = False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'faculty', 'verified', 'created_at']
    list_filter = ['role', 'verified', 'faculty', 'department']
    search_fields = ['user__username', 'user__email', 'matric_number', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'verified')
        }),
        ('Academic Information', {
            'fields': ('department', 'faculty', 'matric_number')
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'order', 'report_count']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    
    def report_count(self, obj):
        return obj.reports.count()
    report_count.short_description = 'Total Reports'


@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'category', 'status', 'reporter', 'is_approved', 
                    'created_at', 'view_count', 'photo_count', 'claim_count']
    list_filter = ['type', 'status', 'is_approved', 'category', 'created_at']
    search_fields = ['title', 'description', 'claim_code', 'reporter__username', 'location_text']
    readonly_fields = ['claim_code', 'created_at', 'updated_at', 'view_count', 'slug']
    date_hierarchy = 'created_at'
    inlines = [ItemPhotoInline, ClaimInline]
    actions = ['approve_reports', 'reject_reports', 'export_as_csv']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('type', 'title', 'description', 'category', 'reporter')
        }),
        ('Location & Date', {
            'fields': ('location_text', 'latitude', 'longitude', 'date_event')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'is_approved', 'claim_code', 'slug', 'reward_offered')
        }),
        ('Metrics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Photos'
    
    def claim_count(self, obj):
        return obj.claims.count()
    claim_count.short_description = 'Claims'
    
    def approve_reports(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reports approved.')
    approve_reports.short_description = 'Approve selected reports'
    
    def reject_reports(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reports rejected.')
    reject_reports.short_description = 'Reject selected reports'
    
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Type', 'Title', 'Category', 'Status', 'Reporter', 
                        'Location', 'Date Event', 'Created At', 'View Count'])
        
        for report in queryset:
            writer.writerow([
                report.id, report.get_type_display(), report.title, 
                report.category.name, report.get_status_display(),
                report.reporter.username, report.location_text,
                report.date_event, report.created_at, report.view_count
            ])
        
        return response
    export_as_csv.short_description = 'Export selected as CSV'


@admin.register(ItemPhoto)
class ItemPhotoAdmin(admin.ModelAdmin):
    list_display = ['report', 'caption', 'uploaded_at', 'image_preview']
    list_filter = ['uploaded_at']
    search_fields = ['report__title', 'caption']
    readonly_fields = ['image_preview', 'uploaded_at']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['report', 'claimant', 'status', 'created_at', 'resolved_at']
    list_filter = ['status', 'created_at', 'resolved_at']
    search_fields = ['report__title', 'claimant__username', 'message']
    readonly_fields = ['created_at', 'resolved_at']
    actions = ['approve_claims', 'reject_claims']
    
    fieldsets = (
        ('Claim Information', {
            'fields': ('report', 'claimant', 'status')
        }),
        ('Details', {
            'fields': ('message', 'evidence_photo', 'resolution_note')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def approve_claims(self, request, queryset):
        for claim in queryset:
            if claim.status == 'PENDING':
                claim.approve()
        self.message_user(request, f'{queryset.count()} claims processed.')
    approve_claims.short_description = 'Approve selected claims'
    
    def reject_claims(self, request, queryset):
        for claim in queryset:
            if claim.status == 'PENDING':
                claim.reject()
        self.message_user(request, f'{queryset.count()} claims processed.')
    reject_claims.short_description = 'Reject selected claims'


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ['report', 'reporter', 'claimant', 'created_at', 'message_count']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['report__title', 'reporter__username', 'claimant__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['thread', 'sender', 'created_at', 'is_read', 'text_preview']
    list_filter = ['is_read', 'created_at']
    search_fields = ['text', 'sender__username']
    readonly_fields = ['created_at']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Message Preview'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'verb', 'target', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['user__username', 'verb']
    readonly_fields = ['created_at']
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark as unread'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'actor', 'target', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['action', 'actor__username']
    readonly_fields = ['actor', 'action', 'target', 'timestamp', 'meta']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['question', 'answer']
    ordering = ['order', 'created_at']


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'description', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(QRTag)
class QRTagAdmin(admin.ModelAdmin):
    list_display = ['code', 'owner', 'item_description', 'is_active', 'scan_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'owner__username', 'item_description']
    readonly_fields = ['code', 'scan_count', 'created_at']

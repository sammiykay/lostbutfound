from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils import timezone
from PIL import Image
import uuid
import string
import random
import os


def generate_claim_code():
    """Generate a unique 8-character claim code"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=8))
        if not ItemReport.objects.filter(claim_code=code).exists():
            return code


def generate_qr_code():
    """Generate a unique QR tag code"""
    return f"QR-{uuid.uuid4().hex[:12].upper()}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('admin', 'Administrator'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=100, blank=True)
    faculty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    matric_number = models.CharField(max_length=20, blank=True, verbose_name="Matric/Staff ID")
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class ItemCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, help_text="Bootstrap icon name (e.g., 'bi-laptop')")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Item Category"
        verbose_name_plural = "Item Categories"
        ordering = ['order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class ItemReport(models.Model):
    TYPE_CHOICES = [
        ('LOST', 'Lost'),
        ('FOUND', 'Found'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLAIMED', 'Claimed'),
        ('RETURNED', 'Returned'),
        ('CLOSED', 'Closed'),
    ]
    
    # Basic Information
    type = models.CharField(max_length=5, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(
        max_length=120,
        validators=[MinLengthValidator(10), MaxLengthValidator(120)],
        help_text="Brief description of the item"
    )
    description = models.TextField(
        validators=[MinLengthValidator(50), MaxLengthValidator(2000)],
        help_text="Detailed description of the item"
    )
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT, related_name='reports')
    
    # Location Information
    location_text = models.CharField(max_length=200, help_text="Where the item was lost/found")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Dates
    date_event = models.DateField(help_text="Date item was lost/found")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional Information
    reward_offered = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Reward amount offered (if any)"
    )
    
    # Status and Tracking
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN', db_index=True)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    claim_code = models.CharField(max_length=8, unique=True, default=generate_claim_code)
    is_approved = models.BooleanField(default=False, db_index=True)
    
    # Admin approval tracking
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reports')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Admin rejection tracking
    is_rejected = models.BooleanField(default=False, db_index=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_reports')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Admin flagging system
    is_flagged = models.BooleanField(default=False, db_index=True)
    flagged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='flagged_reports')
    flagged_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.CharField(max_length=500, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, help_text="Internal notes visible only to staff")
    
    # Metrics
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Item Report"
        verbose_name_plural = "Item Reports"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', 'status', 'is_approved']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['reporter', 'status']),
        ]
    
    def clean(self):
        # Basic model validation - reporter validation moved to view level
        pass
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"
    
    @property
    def slug(self):
        return f"{slugify(self.title)}-{self.claim_code.lower()}"
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


def item_photo_path(instance, filename):
    """Generate upload path for item photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('items', str(instance.report.id), filename)


class ItemPhoto(models.Model):
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=item_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Item Photo"
        verbose_name_plural = "Item Photos"
        ordering = ['uploaded_at']
    
    def clean(self):
        # Validate image size
        if self.image and self.image.size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError("Image file size cannot exceed 5MB.")
        
        # Check photo limit
        if self.pk is None:  # New photo
            photo_count = ItemPhoto.objects.filter(report=self.report).count()
            if photo_count >= 5:
                raise ValidationError("Maximum 5 photos allowed per report.")
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize image if too large
        if self.image:
            img = Image.open(self.image.path)
            if img.height > 1200 or img.width > 1200:
                output_size = (1200, 1200)
                img.thumbnail(output_size)
                img.save(self.image.path)
    
    def __str__(self):
        return f"Photo for {self.report.title}"


class Claim(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COLLECTED', 'Collected'),
    ]
    
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    message = models.TextField(help_text="Describe why this item belongs to you")
    evidence_photo = models.ImageField(upload_to='claims/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    
    # Collection tracking
    collected_at = models.DateTimeField(null=True, blank=True)
    collection_notes = models.TextField(blank=True, help_text="Notes about the collection (location, condition, etc.)")
    collection_confirmed_by_reporter = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        ordering = ['-created_at']
        unique_together = ['report', 'claimant']
    
    def clean(self):
        # Safety check - ensure we have both report and claimant
        if not self.report_id or not self.claimant_id:
            return  # Skip validation if objects aren't set yet
            
        try:
            if self.report.reporter == self.claimant:
                raise ValidationError("You cannot claim your own report.")
        except ItemReport.DoesNotExist:
            raise ValidationError("Invalid report reference.")
    
    def save(self, *args, **kwargs):
        # Standard save - status updates handled in views and approve/reject methods
        super().save(*args, **kwargs)
    
    def update_report_status(self):
        """Update the report status based on claims"""
        # Safety check - ensure the claim has a report
        try:
            if not self.report_id or not self.report:
                return
        except ItemReport.DoesNotExist:
            return
            
        report = self.report
        pending_claims = report.claims.filter(status='PENDING').count()
        approved_claims = report.claims.filter(status='APPROVED').count()
        
        if approved_claims > 0:
            # If there are approved claims, mark as claimed
            if report.status != 'CLAIMED':
                report.status = 'CLAIMED'
                report.save()
        elif pending_claims > 0:
            # If there are pending claims, mark as claimed (under review)
            if report.status == 'OPEN':
                report.status = 'CLAIMED'
                report.save()
        else:
            # No pending claims, check if should revert to OPEN
            if report.status == 'CLAIMED' and approved_claims == 0:
                report.status = 'OPEN'
                report.save()
    
    def approve(self, note=''):
        self.status = 'APPROVED'
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save()
        
        # Update report status based on all claims
        self.update_report_status()
        
        # Create notification
        Notification.objects.create(
            user=self.claimant,
            verb='Your claim has been approved',
            target=self.report
        )
    
    def reject(self, note=''):
        self.status = 'REJECTED'
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save()
        
        # Update report status based on all claims
        self.update_report_status()
        
        # Create notification
        Notification.objects.create(
            user=self.claimant,
            verb='Your claim has been rejected',
            target=self.report
        )
    
    def mark_as_collected(self, notes=''):
        """Mark the claim as collected"""
        if self.status != 'APPROVED':
            raise ValidationError("Only approved claims can be marked as collected.")
        
        self.status = 'COLLECTED'
        self.collected_at = timezone.now()
        self.collection_notes = notes
        self.save()
        
        # Update report status to RETURNED if this was a found item
        if self.report.type == 'FOUND':
            self.report.status = 'RETURNED'
            self.report.save()
        
        # Create notification for both reporter and claimant
        Notification.objects.create(
            user=self.claimant,
            verb=f'Item "{self.report.title}" has been marked as collected',
            target=self.report
        )
        
        if self.claimant != self.report.reporter:
            Notification.objects.create(
                user=self.report.reporter,
                verb=f'Item "{self.report.title}" has been collected by the claimant',
                target=self.report
            )
    
    def __str__(self):
        return f"Claim by {self.claimant.username} for {self.report.title}"


class MessageThread(models.Model):
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='threads')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reporter_threads')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claimant_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Message Thread"
        verbose_name_plural = "Message Threads"
        unique_together = ['report', 'reporter', 'claimant']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Thread: {self.report.title} - {self.claimant.username}"


class Message(models.Model):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    image = models.ImageField(upload_to='messages/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=255)
    
    # Generic Foreign Key for target
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.verb} - {self.user.username}"


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    
    # Generic Foreign Key for target
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} by {self.actor} at {self.timestamp}"


class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return self.question


class StaticPage(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Static Page"
        verbose_name_plural = "Static Pages"
    
    def __str__(self):
        return self.title


class SiteSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return self.key


class QRTag(models.Model):
    code = models.CharField(max_length=20, unique=True, default=generate_qr_code)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='qr_tags')
    item_description = models.CharField(max_length=200, blank=True)
    contact_info = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    scan_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "QR Tag"
        verbose_name_plural = "QR Tags"
    
    def __str__(self):
        return f"QR Tag: {self.code}"
    
    def increment_scan_count(self):
        self.scan_count += 1
        self.save(update_fields=['scan_count'])

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView
)
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import qrcode
from io import BytesIO
import base64

from .models import (
    ItemReport, ItemCategory, ItemPhoto, Claim, Message, 
    MessageThread, UserProfile, Notification, FAQ, StaticPage, QRTag
)
from .forms import (
    CustomUserCreationForm, UserProfileForm, ItemReportForm,
    ClaimForm, MessageForm, ReportSearchForm, ClaimResolutionForm,
    ReportStatusForm, BulkPhotoUploadForm
)


class HomeView(TemplateView):
    template_name = 'lost_found/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent approved reports
        recent_lost = ItemReport.objects.filter(
            is_approved=True, type='LOST', status='OPEN'
        ).select_related('category', 'reporter')[:6]
        
        recent_found = ItemReport.objects.filter(
            is_approved=True, type='FOUND', status='OPEN'
        ).select_related('category', 'reporter')[:6]
        
        # Get categories
        categories = ItemCategory.objects.annotate(
            report_count=Count('reports', filter=Q(reports__is_approved=True))
        )
        
        # Get statistics
        stats = {
            'total_reports': ItemReport.objects.filter(is_approved=True).count(),
            'resolved_reports': ItemReport.objects.filter(
                is_approved=True, status__in=['RETURNED', 'CLAIMED']
            ).count(),
            'active_reports': ItemReport.objects.filter(
                is_approved=True, status='OPEN'
            ).count(),
        }
        
        context.update({
            'recent_lost': recent_lost,
            'recent_found': recent_found,
            'categories': categories,
            'stats': stats,
        })
        return context


class ReportListView(ListView):
    model = ItemReport
    template_name = 'lost_found/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ItemReport.objects.filter(is_approved=True).select_related(
            'category', 'reporter'
        ).prefetch_related('photos')
        
        # Apply search filters
        form = ReportSearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get('q')
            if q:
                queryset = queryset.filter(
                    Q(title__icontains=q) |
                    Q(description__icontains=q) |
                    Q(location_text__icontains=q)
                )
            
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            report_type = form.cleaned_data.get('type')
            if report_type:
                queryset = queryset.filter(type=report_type)
            
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            location = form.cleaned_data.get('location')
            if location:
                queryset = queryset.filter(location_text__icontains=location)
            
            if form.cleaned_data.get('with_photos'):
                queryset = queryset.filter(photos__isnull=False).distinct()
            
            if form.cleaned_data.get('unclaimed_only'):
                queryset = queryset.filter(status='OPEN')
            
            # Date filters
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            if date_from:
                queryset = queryset.filter(date_event__gte=date_from)
            if date_to:
                queryset = queryset.filter(date_event__lte=date_to)
            
            # Sorting
            sort = form.cleaned_data.get('sort', '-created_at')
            if sort:
                queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ReportSearchForm(self.request.GET)
        context['categories'] = ItemCategory.objects.all()
        return context


class ReportDetailView(DetailView):
    model = ItemReport
    template_name = 'lost_found/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        return ItemReport.objects.filter(is_approved=True).select_related(
            'category', 'reporter'
        ).prefetch_related('photos', 'claims')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.increment_view_count()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user can claim this item
        can_claim = False
        user_claim = None
        if self.request.user.is_authenticated:
            can_claim = (
                self.request.user != self.object.reporter and
                self.object.status == 'OPEN' and
                not self.object.claims.filter(claimant=self.request.user).exists()
            )
            try:
                user_claim = self.object.claims.get(claimant=self.request.user)
            except Claim.DoesNotExist:
                pass
        
        context.update({
            'can_claim': can_claim,
            'user_claim': user_claim,
            'claim_form': ClaimForm(),
        })
        return context


class ReportCreateView(LoginRequiredMixin, CreateView):
    model = ItemReport
    form_class = ItemReportForm
    template_name = 'lost_found/report_form.html'
    
    def form_valid(self, form):
        # Check active reports limit before saving
        active_reports = ItemReport.objects.filter(
            reporter=self.request.user,
            status='OPEN'
        ).count()
        if active_reports >= 5:
            form.add_error(None, "You cannot have more than 5 active open reports. Please wait for some to be resolved.")
            return self.form_invalid(form)
        
        form.instance.reporter = self.request.user
        response = super().form_valid(form)
        
        # Handle photo uploads
        photos = self.request.FILES.getlist('photos')
        for photo in photos:
            ItemPhoto.objects.create(
                report=self.object,
                image=photo
            )
        
        messages.success(
            self.request,
            'Your report has been submitted and is pending approval.'
        )
        return response
    
    def get_success_url(self):
        return reverse('lost_found:report_success', args=[self.object.pk])


class ReportSuccessView(LoginRequiredMixin, DetailView):
    model = ItemReport
    template_name = 'lost_found/report_success.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        # Only allow users to see success page for their own reports
        return ItemReport.objects.filter(reporter=self.request.user)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'lost_found/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User's reports
        my_reports = ItemReport.objects.filter(reporter=user).order_by('-created_at')[:10]
        
        # User's claims
        my_claims = Claim.objects.filter(claimant=user).select_related('report').order_by('-created_at')[:10]
        
        # Pending claims on user's reports
        pending_claims = Claim.objects.filter(
            report__reporter=user, status='PENDING'
        ).select_related('report', 'claimant')[:5]
        
        # Recent notifications
        notifications = Notification.objects.filter(
            user=user, is_read=False
        ).select_related('target_content_type')[:5]
        
        context.update({
            'my_reports': my_reports,
            'my_claims': my_claims,
            'pending_claims': pending_claims,
            'notifications': notifications,
        })
        return context


class ClaimCreateView(LoginRequiredMixin, CreateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'lost_found/claim_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        try:
            # Only get approved reports for claiming
            self.report = get_object_or_404(ItemReport, pk=kwargs['pk'], is_approved=True)
        except ItemReport.DoesNotExist:
            messages.error(request, "The requested report was not found or is not available for claims.")
            return redirect('lost_found:report_list')
        
        # Check if user can claim
        if request.user == self.report.reporter:
            messages.error(request, "You cannot claim your own report.")
            return redirect('lost_found:report_detail', pk=self.report.pk)
        
        if self.report.status not in ['OPEN', 'CLAIMED']:
            messages.error(request, "This item is no longer available for claims.")
            return redirect('lost_found:report_detail', pk=self.report.pk)
        
        # Check if user already has a claim
        if Claim.objects.filter(report=self.report, claimant=request.user).exists():
            messages.error(request, "You have already submitted a claim for this item.")
            return redirect('lost_found:report_detail', pk=self.report.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Ensure report and claimant are properly set before saving
        form.instance.report = self.report
        form.instance.claimant = self.request.user
        
        # Save the claim first
        response = super().form_valid(form)
        
        # Update report status after claim is created successfully
        self.report.refresh_from_db()  # Ensure we have the latest data
        if self.report.status == 'OPEN':
            self.report.status = 'CLAIMED'
            self.report.save()
        
        # Create notification for reporter (only after successful save)
        try:
            Notification.objects.create(
                user=self.report.reporter,
                verb=f'New claim submitted for "{self.report.title}"',
                target=self.object
            )
        except Exception:
            # Don't fail the entire process if notification fails
            pass
        
        messages.success(
            self.request,
            'Your claim has been submitted. The item owner will review it.'
        )
        return response
    
    def get_success_url(self):
        return reverse('lost_found:report_detail', args=[self.report.pk])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.report
        return context


class RegisterView(FormView):
    template_name = 'registration/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('lost_found:home')
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Account created successfully!')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'lost_found/profile.html'


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'lost_found/profile_edit.html'
    success_url = reverse_lazy('lost_found:profile')
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ClaimListView(LoginRequiredMixin, ListView):
    model = Claim
    template_name = 'lost_found/claim_list.html'
    context_object_name = 'claims'
    paginate_by = 20
    
    def get_queryset(self):
        return Claim.objects.filter(
            claimant=self.request.user
        ).select_related('report').order_by('-created_at')


class StaticPageView(DetailView):
    model = StaticPage
    template_name = 'lost_found/static_page.html'
    context_object_name = 'page'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return StaticPage.objects.filter(is_active=True)


class FAQView(ListView):
    model = FAQ
    template_name = 'lost_found/faq.html'
    context_object_name = 'faqs'
    
    def get_queryset(self):
        return FAQ.objects.filter(is_active=True).order_by('order', 'created_at')


# Simple stub views for features that would require full implementation
class ReportUpdateView(LoginRequiredMixin, UpdateView):
    model = ItemReport
    form_class = ItemReportForm
    template_name = 'lost_found/report_form.html'


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    model = ItemReport
    success_url = reverse_lazy('lost_found:dashboard')


class ClaimDetailView(LoginRequiredMixin, DetailView):
    model = Claim
    template_name = 'lost_found/claim_detail.html'


class MessageThreadListView(LoginRequiredMixin, ListView):
    model = MessageThread
    template_name = 'lost_found/message_list.html'


class MessageThreadDetailView(LoginRequiredMixin, DetailView):
    model = MessageThread
    template_name = 'lost_found/message_detail.html'


class QRTagView(DetailView):
    model = QRTag
    template_name = 'lost_found/qr_tag.html'


class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'lost_found/admin_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dashboard statistics
        context.update({
            'total_reports': ItemReport.objects.count(),
            'pending_reports': ItemReport.objects.filter(is_approved=False).count(),
            'resolved_reports': ItemReport.objects.filter(status__in=['RETURNED', 'CLAIMED']).count(),
            'flagged_count': ItemReport.objects.filter(is_flagged=True).count(),
            'total_users': ItemReport.objects.values('reporter').distinct().count(),
            'active_users': ItemReport.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).values('reporter').distinct().count(),
        })
        
        return context


class AdminReportListView(UserPassesTestMixin, ListView):
    model = ItemReport
    template_name = 'lost_found/admin_report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        queryset = ItemReport.objects.select_related(
            'reporter', 'category'
        ).prefetch_related('photos').order_by('-created_at')
        
        # Filter by status
        status_filter = self.request.GET.get('status', 'all')
        if status_filter == 'pending':
            queryset = queryset.filter(is_approved=False)
        elif status_filter == 'approved':
            queryset = queryset.filter(is_approved=True)
        elif status_filter == 'flagged':
            queryset = queryset.filter(is_flagged=True)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reporter__username__icontains=search_query) |
                Q(reporter__email__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter counts
        context.update({
            'total_count': ItemReport.objects.count(),
            'pending_count': ItemReport.objects.filter(is_approved=False).count(),
            'approved_count': ItemReport.objects.filter(is_approved=True).count(),
            'flagged_count': ItemReport.objects.filter(is_flagged=True).count(),
            'current_status': self.request.GET.get('status', 'all'),
            'search_query': self.request.GET.get('search', ''),
        })
        
        return context


class AnalyticsView(UserPassesTestMixin, TemplateView):
    template_name = 'lost_found/analytics.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic analytics data
        total_reports = ItemReport.objects.count()
        resolved_reports = ItemReport.objects.filter(status__in=['RETURNED', 'CLAIMED']).count()
        
        context.update({
            'total_reports': total_reports,
            'success_rate': round((resolved_reports / total_reports * 100) if total_reports > 0 else 0, 1),
            'avg_resolution_time': 5,  # Placeholder - would calculate actual average
            'active_users': ItemReport.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).values('reporter').distinct().count(),
        })
        
        return context


# Function-based views for AJAX endpoints
@login_required
@require_http_methods(["POST"])
def update_report_status(request, pk):
    report = get_object_or_404(ItemReport, pk=pk)
    
    if request.user != report.reporter and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    form = ReportStatusForm(request.POST)
    if form.is_valid():
        report.status = form.cleaned_data['status']
        report.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Invalid form'}, status=400)


@login_required
@require_http_methods(["POST"])
def approve_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if request.user != claim.report.reporter and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    claim.approve()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def reject_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if request.user != claim.report.reporter and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    claim.reject()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def send_message(request):
    # Placeholder for message sending
    return JsonResponse({'success': True})


# Admin approval functions
@login_required
@require_http_methods(["POST"])
def approve_report(request, pk):
    """Approve a pending report"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    report = get_object_or_404(ItemReport, pk=pk)
    
    if report.is_approved:
        return JsonResponse({'error': 'Report is already approved'}, status=400)
    
    # Approve the report
    report.is_approved = True
    report.approved_by = request.user
    report.approved_at = timezone.now()
    report.save()
    
    # Create notification for the reporter
    Notification.objects.create(
        user=report.reporter,
        verb=f'Your report "{report.title}" has been approved and is now live',
        target=report
    )
    
    messages.success(request, f'Report "{report.title}" has been approved.')
    
    return JsonResponse({
        'success': True,
        'message': 'Report approved successfully',
        'report_id': report.pk
    })


@login_required
@require_http_methods(["POST"])
def reject_report(request, pk):
    """Reject a pending report"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    report = get_object_or_404(ItemReport, pk=pk)
    
    if report.is_approved:
        return JsonResponse({'error': 'Cannot reject an approved report'}, status=400)
    
    # Get rejection reason from request
    rejection_reason = request.POST.get('reason', 'No reason provided')
    
    # Mark as rejected (you might want to add a rejected field to the model)
    report.is_rejected = True
    report.rejected_by = request.user
    report.rejected_at = timezone.now()
    report.rejection_reason = rejection_reason
    report.save()
    
    # Create notification for the reporter
    Notification.objects.create(
        user=report.reporter,
        verb=f'Your report "{report.title}" was not approved. Reason: {rejection_reason}',
        target=report
    )
    
    messages.info(request, f'Report "{report.title}" has been rejected.')
    
    return JsonResponse({
        'success': True,
        'message': 'Report rejected',
        'report_id': report.pk
    })


@login_required
@require_http_methods(["POST"])
def flag_report(request, pk):
    """Flag a report for review"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    report = get_object_or_404(ItemReport, pk=pk)
    
    # Get flag reason from request
    flag_reason = request.POST.get('reason', 'Flagged for review')
    
    # Flag the report
    report.is_flagged = True
    report.flagged_by = request.user
    report.flagged_at = timezone.now()
    report.flag_reason = flag_reason
    report.save()
    
    messages.warning(request, f'Report "{report.title}" has been flagged for review.')
    
    return JsonResponse({
        'success': True,
        'message': 'Report flagged for review',
        'report_id': report.pk
    })


@login_required
@require_http_methods(["POST"])
def unflag_report(request, pk):
    """Remove flag from a report"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    report = get_object_or_404(ItemReport, pk=pk)
    
    # Unflag the report
    report.is_flagged = False
    report.flagged_by = None
    report.flagged_at = None
    report.flag_reason = ''
    report.save()
    
    messages.success(request, f'Flag removed from report "{report.title}".')
    
    return JsonResponse({
        'success': True,
        'message': 'Report flag removed',
        'report_id': report.pk
    })


@login_required
def admin_report_detail(request, pk):
    """Admin-specific report detail view with approval actions"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('lost_found:home')
    
    report = get_object_or_404(ItemReport, pk=pk)
    
    # Calculate reporter statistics
    reporter = report.reporter
    reporter_stats = {
        'total_reports': reporter.reports.count(),
        'approved_reports': reporter.reports.filter(is_approved=True).count(),
        'claims_made': reporter.claims.count(),
        'approved_claims': reporter.claims.filter(status='APPROVED').count(),
    }
    
    context = {
        'report': report,
        'claims': report.claims.select_related('claimant').order_by('-created_at'),
        'can_approve': not report.is_approved and not getattr(report, 'is_rejected', False),
        'can_reject': not report.is_approved and not getattr(report, 'is_rejected', False),
        'can_flag': not report.is_flagged,
        'can_unflag': report.is_flagged,
        'reporter_stats': reporter_stats,
    }
    
    return render(request, 'lost_found/admin_report_detail.html', context)


@login_required
def admin_counts_api(request):
    """API endpoint for admin badge counts"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    counts = {
        'pending_reports': ItemReport.objects.filter(is_approved=False, is_rejected=False).count(),
        'flagged_reports': ItemReport.objects.filter(is_flagged=True).count(),
        'total_reports': ItemReport.objects.count(),
        'approved_reports': ItemReport.objects.filter(is_approved=True).count(),
    }
    
    return JsonResponse(counts)


@login_required
def notifications_api(request):
    """API endpoint for user notifications"""
    # Get all notifications for user first
    all_notifications = Notification.objects.filter(
        user=request.user
    ).select_related('target_content_type').order_by('-created_at')
    
    # Get unread count before slicing
    unread_count = all_notifications.filter(is_read=False).count()
    
    # Get latest 10 notifications
    notifications = all_notifications[:10]
    
    # Convert notifications to JSON-serializable format
    results = []
    for notification in notifications:
        results.append({
            'id': notification.id,
            'verb': notification.verb,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
        })
    
    return JsonResponse({
        'results': results,
        'unread_count': unread_count
    })


@login_required
@require_http_methods(["POST"])
def mark_notifications_read(request):
    """Mark user notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def mark_as_collected(request, pk):
    """Mark a claim as collected"""
    claim = get_object_or_404(Claim, pk=pk)
    
    # Check permissions - either reporter, claimant, or staff can mark as collected
    if not (request.user == claim.report.reporter or 
            request.user == claim.claimant or 
            request.user.is_staff):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if claim.status != 'APPROVED':
        return JsonResponse({'error': 'Only approved claims can be marked as collected'}, status=400)
    
    # Get collection notes from request
    collection_notes = request.POST.get('notes', '')
    
    try:
        claim.mark_as_collected(collection_notes)
        
        messages.success(
            request, 
            f'Claim for "{claim.report.title}" has been marked as collected.'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Claim marked as collected successfully',
            'claim_id': claim.pk
        })
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'An error occurred while marking as collected'}, status=500)


def generate_qr_code(request, pk):
    report = get_object_or_404(ItemReport, pk=pk)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(request.build_absolute_uri(
        reverse('lost_found:report_detail', args=[report.pk])
    ))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for embedding in template
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer.getvalue(), content_type="image/png")



def logout_view(request):
    """Custom logout view to add a message"""
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('lost_found:home')
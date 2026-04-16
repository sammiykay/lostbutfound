from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Field
from crispy_forms.bootstrap import FormActions
from .models import (
    ItemReport, ItemPhoto, Claim, UserProfile, 
    Message, MessageThread
)
import re


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    # Profile fields
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        help_text="Select your role at the university"
    )
    department = forms.CharField(max_length=100, required=False)
    faculty = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=20, required=False)
    matric_number = forms.CharField(
        max_length=20, 
        required=False,
        label="Matric/Staff ID",
        help_text="Your student matriculation number or staff ID"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Account Information',
                Row(
                    Column('first_name', css_class='form-group col-md-6 mb-3'),
                    Column('last_name', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
                Row(
                    Column('username', css_class='form-group col-md-6 mb-3'),
                    Column('email', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
                Row(
                    Column('password1', css_class='form-group col-md-6 mb-3'),
                    Column('password2', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'University Information',
                Row(
                    Column('role', css_class='form-group col-md-4 mb-3'),
                    Column('matric_number', css_class='form-group col-md-4 mb-3'),
                    Column('phone', css_class='form-group col-md-4 mb-3'),
                    css_class='form-row'
                ),
                Row(
                    Column('department', css_class='form-group col-md-6 mb-3'),
                    Column('faculty', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
            ),
            FormActions(
                Submit('submit', 'Create Account', css_class='btn btn-primary btn-lg')
            )
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already registered.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                department=self.cleaned_data.get('department', ''),
                faculty=self.cleaned_data.get('faculty', ''),
                phone=self.cleaned_data.get('phone', ''),
                matric_number=self.cleaned_data.get('matric_number', ''),
            )
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = UserProfile
        fields = ['role', 'department', 'faculty', 'phone', 'matric_number']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Row(
                    Column('first_name', css_class='form-group col-md-6 mb-3'),
                    Column('last_name', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
                Field('email'),
            ),
            Fieldset(
                'University Information',
                Row(
                    Column('role', css_class='form-group col-md-4 mb-3'),
                    Column('matric_number', css_class='form-group col-md-4 mb-3'),
                    Column('phone', css_class='form-group col-md-4 mb-3'),
                    css_class='form-row'
                ),
                Row(
                    Column('department', css_class='form-group col-md-6 mb-3'),
                    Column('faculty', css_class='form-group col-md-6 mb-3'),
                    css_class='form-row'
                ),
            ),
            FormActions(
                Submit('submit', 'Update Profile', css_class='btn btn-primary')
            )
        )


class ItemReportForm(forms.ModelForm):
    latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = ItemReport
        fields = [
            'type', 'title', 'description', 'category', 'location_text',
            'latitude', 'longitude', 'date_event', 'reward_offered'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'date_event': forms.DateInput(attrs={'type': 'date'}),
            'reward_offered': forms.NumberInput(attrs={'step': '0.01', 'min': '0'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields more user-friendly
        self.fields['type'].widget = forms.RadioSelect()
        self.fields['title'].help_text = "Brief, descriptive title (10-120 characters)"
        self.fields['description'].help_text = "Detailed description including color, brand, unique features (50-2000 characters)"
        self.fields['location_text'].help_text = "Where was the item lost/found? Be as specific as possible"
        self.fields['date_event'].help_text = "When did you lose/find this item?"
        self.fields['reward_offered'].help_text = "Optional: Reward amount you're willing to offer"
        
        self.helper = FormHelper()
        self.helper.form_id = 'report-form'
        self.helper.layout = Layout(
            Fieldset(
                'Report Type',
                Field('type', css_class='form-check-input'),
            ),
            Fieldset(
                'Item Details',
                Row(
                    Column('title', css_class='form-group col-md-8 mb-3'),
                    Column('category', css_class='form-group col-md-4 mb-3'),
                    css_class='form-row'
                ),
                Field('description'),
            ),
            Fieldset(
                'Location & Date',
                Row(
                    Column('location_text', css_class='form-group col-md-8 mb-3'),
                    Column('date_event', css_class='form-group col-md-4 mb-3'),
                    css_class='form-row'
                ),
                Field('latitude'),
                Field('longitude'),
                HTML('<div id="map-container" style="height: 300px; margin: 15px 0;"></div>'),
            ),
            Fieldset(
                'Additional Information',
                Field('reward_offered'),
            ),
            HTML('<div id="photo-upload-section" class="mb-4"></div>'),
            FormActions(
                Submit('submit', 'Submit Report', css_class='btn btn-primary btn-lg')
            )
        )


class ItemPhotoForm(forms.ModelForm):
    class Meta:
        model = ItemPhoto
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            }),
            'caption': forms.TextInput(attrs={'placeholder': 'Optional caption'})
        }


class ReportSearchForm(forms.Form):
    SORT_CHOICES = [
        ('-created_at', 'Newest First'),
        ('created_at', 'Oldest First'),
        ('-view_count', 'Most Viewed'),
        ('-updated_at', 'Recently Updated'),
    ]
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by title, description, or location...',
            'class': 'form-control'
        }),
        label='Search'
    )
    category = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    type = forms.ChoiceField(
        choices=[('', 'Lost & Found')] + ItemReport.TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + ItemReport.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Filter by location...',
            'class': 'form-control'
        })
    )
    with_photos = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    unclaimed_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        from .models import ItemCategory
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ItemCategory.objects.all()


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['message', 'evidence_photo']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Please describe why this item belongs to you. Include any identifying details that prove ownership...'
            }),
            'evidence_photo': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message'].help_text = "Provide specific details that prove this item is yours"
        self.fields['evidence_photo'].help_text = "Optional: Upload a photo that helps prove ownership"
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('message'),
            Field('evidence_photo'),
            FormActions(
                Submit('submit', 'Submit Claim', css_class='btn btn-primary')
            )
        )


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'image']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Type your message...',
                'class': 'form-control'
            }),
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].label = ''
        self.fields['image'].label = 'Attach Image'
        self.fields['image'].required = False
        
        self.helper = FormHelper()
        self.helper.form_id = 'message-form'
        self.helper.form_class = 'message-form'
        self.helper.layout = Layout(
            Field('text'),
            Field('image'),
            FormActions(
                Submit('submit', 'Send Message', css_class='btn btn-primary')
            )
        )


class ClaimResolutionForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.HiddenInput()
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Optional note about the decision...'
        }),
        label='Resolution Note'
    )


class ReportStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('CLAIMED', 'Mark as Claimed'),
        ('RETURNED', 'Mark as Returned'),
        ('CLOSED', 'Close Report'),
    ]
    
    status = forms.ChoiceField(choices=STATUS_CHOICES)
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Optional note about status change...'
        })
    )


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BulkPhotoUploadForm(forms.Form):
    photos = MultipleFileField(
        required=False,
        help_text="Select up to 5 photos. Supported formats: JPG, PNG, WebP"
    )
    
    def clean_photos(self):
        photos = self.cleaned_data.get('photos')
        if not photos:
            return photos
        
        if isinstance(photos, list):
            if len(photos) > 5:
                raise ValidationError("Maximum 5 photos allowed.")
            
            for photo in photos:
                # Validate file size (5MB max)
                if photo.size > 5 * 1024 * 1024:
                    raise ValidationError(f"File {photo.name} is too large. Maximum size is 5MB.")
                
                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
                if photo.content_type not in allowed_types:
                    raise ValidationError(f"File {photo.name} is not a supported image format.")
        
        return photos
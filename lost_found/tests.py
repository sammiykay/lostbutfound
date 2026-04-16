from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from decimal import Decimal
from datetime import date, timedelta
import json

from .models import (
    ItemReport, ItemCategory, UserProfile, ItemPhoto, 
    Claim, Notification, MessageThread, Message
)


class ItemReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = ItemCategory.objects.create(
            name='Electronics',
            slug='electronics',
            icon='bi-laptop'
        )
    
    def test_create_item_report(self):
        report = ItemReport.objects.create(
            type='LOST',
            title='Lost iPhone 13',
            description='Black iPhone 13 Pro Max lost in the library on second floor',
            category=self.category,
            location_text='Main Library - 2nd Floor',
            date_event=date.today(),
            reporter=self.user
        )
        
        self.assertEqual(report.status, 'OPEN')
        self.assertFalse(report.is_approved)
        self.assertEqual(report.view_count, 0)
        self.assertTrue(len(report.claim_code) == 8)
    
    def test_generate_slug(self):
        report = ItemReport.objects.create(
            type='FOUND',
            title='Found MacBook Pro',
            description='Silver MacBook Pro found in cafeteria',
            category=self.category,
            location_text='Main Cafeteria',
            date_event=date.today(),
            reporter=self.user
        )
        
        expected_slug = f"found-macbook-pro-{report.claim_code.lower()}"
        self.assertEqual(report.slug, expected_slug)
    
    def test_increment_view_count(self):
        report = ItemReport.objects.create(
            type='LOST',
            title='Lost Wallet',
            description='Brown leather wallet',
            category=self.category,
            location_text='Student Union',
            date_event=date.today(),
            reporter=self.user
        )
        
        initial_count = report.view_count
        report.increment_view_count()
        self.assertEqual(report.view_count, initial_count + 1)


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ItemCategory.objects.create(
            name='Electronics',
            slug='electronics',
            icon='bi-laptop'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_home_page_loads(self):
        response = self.client.get(reverse('lost_found:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lost Something? Found Something?')
    
    def test_home_page_shows_statistics(self):
        # Create some test data
        ItemReport.objects.create(
            type='LOST',
            title='Test Item',
            description='Test description for this lost item with enough characters',
            category=self.category,
            location_text='Test Location',
            date_event=date.today(),
            reporter=self.user,
            is_approved=True
        )
        
        response = self.client.get(reverse('lost_found:home'))
        self.assertEqual(response.status_code, 200)


class AuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_required_for_dashboard(self):
        response = self.client.get(reverse('lost_found:dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/dashboard/')
    
    def test_successful_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/dashboard/')
    
    def test_dashboard_accessible_after_login(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('lost_found:dashboard'))
        self.assertEqual(response.status_code, 200)

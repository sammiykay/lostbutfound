from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from faker import Faker
import random
import os
import io
from PIL import Image, ImageDraw
from django.core.files.uploadedfile import SimpleUploadedFile
from lost_found.models import (
    UserProfile, ItemCategory, ItemReport, ItemPhoto, 
    Claim, FAQ, StaticPage, SiteSetting
)


class Command(BaseCommand):
    help = 'Seed database with sample data'
    
    def __init__(self):
        super().__init__()
        self.fake = Faker()
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--users', type=int, default=20,
            help='Number of users to create (default: 20)'
        )
        parser.add_argument(
            '--reports', type=int, default=50,
            help='Number of reports to create (default: 50)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')
        
        # Load categories first
        self.create_categories()
        
        # Create admin user
        self.create_admin_user()
        
        # Create sample users
        users_count = options['users']
        users = self.create_users(users_count)
        
        # Create sample reports
        reports_count = options['reports']
        self.create_reports(users, reports_count)
        
        # Create FAQs
        self.create_faqs()
        
        # Create static pages
        self.create_static_pages()
        
        # Create site settings
        self.create_site_settings()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully seeded database with:')
        )
        self.stdout.write(f'  - 1 admin user (admin@example.com / Admin123!)')
        self.stdout.write(f'  - {users_count} sample users')
        self.stdout.write(f'  - 8 categories')
        self.stdout.write(f'  - {reports_count} item reports')
        self.stdout.write(f'  - FAQs, static pages, and site settings')
        self.stdout.write('')
        self.stdout.write('Demo logins:')
        self.stdout.write('  Admin: admin@example.com / Admin123!')
        self.stdout.write('  Student: user1@example.com / User123!')
        self.stdout.write('  Staff: user2@example.com / User123!')
    
    def create_categories(self):
        self.stdout.write('Creating categories...')
        from django.core.management import call_command
        call_command('loaddata', 'categories')
    
    def create_admin_user(self):
        self.stdout.write('Creating admin user...')
        if not User.objects.filter(email='admin@example.com').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='Admin123!',
                first_name='Admin',
                last_name='User'
            )
            UserProfile.objects.create(
                user=admin_user,
                role='admin',
                department='IT',
                faculty='Administration',
                phone='+1234567890',
                matric_number='ADMIN001',
                verified=True
            )
    
    def create_users(self, count):
        self.stdout.write(f'Creating {count} sample users...')
        users = []
        
        # Create specific demo users
        demo_users = [
            {
                'username': 'user1',
                'email': 'user1@example.com',
                'password': 'User123!',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'student',
                'department': 'Computer Science',
                'faculty': 'Engineering',
                'matric_number': 'CS20240001'
            },
            {
                'username': 'user2',
                'email': 'user2@example.com',
                'password': 'User123!',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'staff',
                'department': 'Student Affairs',
                'faculty': 'Administration',
                'matric_number': 'STAFF002'
            }
        ]
        
        for user_data in demo_users:
            if not User.objects.filter(email=user_data['email']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                UserProfile.objects.create(
                    user=user,
                    role=user_data['role'],
                    department=user_data['department'],
                    faculty=user_data['faculty'],
                    phone=self.fake.phone_number()[:20],
                    matric_number=user_data['matric_number'],
                    verified=True
                )
                users.append(user)
        
        # Create additional random users
        departments = ['Computer Science', 'Mathematics', 'Physics', 'Chemistry', 
                      'Biology', 'English', 'History', 'Psychology', 'Economics']
        faculties = ['Engineering', 'Science', 'Arts', 'Business', 'Medicine']
        
        for i in range(3, count + 1):
            username = f'user{i}'
            email = f'user{i}@example.com'
            
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='User123!',
                    first_name=self.fake.first_name(),
                    last_name=self.fake.last_name()
                )
                
                role = random.choice(['student', 'staff'])
                dept = random.choice(departments)
                faculty = random.choice(faculties)
                
                UserProfile.objects.create(
                    user=user,
                    role=role,
                    department=dept,
                    faculty=faculty,
                    phone=self.fake.phone_number()[:20],
                    matric_number=f'{dept[:2].upper()}{random.randint(20240000, 20249999)}',
                    verified=random.choice([True, False])
                )
                users.append(user)
        
        return users
    
    def create_placeholder_image(self, name="placeholder"):
        """Create a simple placeholder image"""
        img = Image.new('RGB', (400, 300), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((150, 140), f"{name.upper()}", fill=(100, 100, 100))
        
        # Save to in-memory file
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        return SimpleUploadedFile(
            f"{name}.jpg",
            img_io.getvalue(),
            content_type="image/jpeg"
        )
    
    def create_reports(self, users, count):
        self.stdout.write(f'Creating {count} item reports...')
        categories = list(ItemCategory.objects.all())
        
        # Sample data for different types of items
        lost_items = [
            ('iPhone 13 Pro Max', 'Black iPhone 13 Pro Max with cracked screen protector'),
            ('Lenovo ThinkPad Laptop', 'Black Lenovo ThinkPad with university stickers'),
            ('Student ID Card', 'University student ID card with photo'),
            ('Calculus Textbook', 'Stewart Calculus textbook, 8th edition'),
            ('North Face Jacket', 'Blue North Face winter jacket, size M'),
            ('Toyota Car Keys', 'Toyota car keys with Toyota keychain'),
            ('Apple Watch Series 8', 'Silver Apple Watch with sport band'),
            ('Black Wallet', 'Black leather wallet with multiple cards'),
            ('Wireless Earbuds', 'White Apple AirPods Pro'),
            ('Prescription Glasses', 'Black-rimmed prescription glasses'),
        ]
        
        found_items = [
            ('Samsung Galaxy Phone', 'Found Samsung Galaxy phone in library'),
            ('MacBook Air', 'Silver MacBook Air found in cafeteria'),
            ('Staff Access Card', 'University staff access card'),
            ('Chemistry Lab Manual', 'Organic chemistry lab manual'),
            ('Red Hoodie', 'Red university hoodie, size L'),
            ('House Keys', 'Set of house keys with Hello Kitty keychain'),
            ('Fitbit Watch', 'Black Fitbit fitness tracker'),
            ('Brown Purse', 'Brown leather purse with contents'),
            ('Bluetooth Headphones', 'Black over-ear Bluetooth headphones'),
            ('Reading Glasses', 'Gold-rimmed reading glasses in case'),
        ]
        
        # Campus locations
        locations = [
            'Main Library - 2nd Floor',
            'Student Union Building',
            'Engineering Building - Room 205',
            'Cafeteria - Near entrance',
            'Parking Lot B',
            'Gymnasium - Locker room',
            'Science Building - Lab 301',
            'Administration Building - 1st Floor',
            'Dormitory Building A',
            'Computer Lab - Room 150',
            'Lecture Hall C',
            'Campus Bookstore',
            'Health Center',
            'Arts Building - Studio 4',
            'Mathematics Department'
        ]
        
        for i in range(count):
            # Choose random type and corresponding item data
            report_type = random.choice(['LOST', 'FOUND'])
            if report_type == 'LOST':
                title, description = random.choice(lost_items)
            else:
                title, description = random.choice(found_items)
            
            # Add variation to title and description
            title = f"{title} - {self.fake.word().title()}"
            description = f"{description}. {self.fake.sentence()}"
            
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            event_date = date.today() - timedelta(days=days_ago)
            
            # Create report
            report = ItemReport.objects.create(
                type=report_type,
                title=title,
                description=description,
                category=random.choice(categories),
                location_text=random.choice(locations),
                latitude=random.uniform(1.2800, 1.3600),  # Singapore coordinates
                longitude=random.uniform(103.6000, 103.9000),
                date_event=event_date,
                reward_offered=random.choice([None, None, None, 50.00, 100.00, 25.00]),
                status=random.choice(['OPEN', 'OPEN', 'OPEN', 'CLAIMED', 'RETURNED', 'CLOSED']),
                reporter=random.choice(users),
                is_approved=random.choice([True, True, True, False]),  # Mostly approved
                view_count=random.randint(0, 100)
            )
            
            # Add 1-3 photos to some reports
            if random.random() < 0.7:  # 70% chance of having photos
                photo_count = random.randint(1, 3)
                for j in range(photo_count):
                    photo_image = self.create_placeholder_image(f"item_{report.id}_{j}")
                    ItemPhoto.objects.create(
                        report=report,
                        image=photo_image,
                        caption=f"Photo {j+1} of {report.title}"
                    )
            
            # Add claims to some reports
            if report.status in ['CLAIMED', 'RETURNED'] and random.random() < 0.8:
                claimant = random.choice([u for u in users if u != report.reporter])
                claim = Claim.objects.create(
                    report=report,
                    claimant=claimant,
                    message=f"This is my {report.title.lower()}. {self.fake.sentence()}",
                    status=random.choice(['APPROVED', 'APPROVED', 'PENDING', 'REJECTED'])
                )
                
                if claim.status == 'APPROVED':
                    claim.resolved_at = timezone.now() - timedelta(
                        days=random.randint(1, days_ago)
                    )
                    claim.save()
    
    def create_faqs(self):
        self.stdout.write('Creating FAQs...')
        faqs = [
            {
                'question': 'How do I report a lost item?',
                'answer': 'Click on "Report an Item" button, select "Lost", fill in the details including photos and location where you lost it.',
                'order': 1
            },
            {
                'question': 'How do I report a found item?',
                'answer': 'Click on "Report an Item" button, select "Found", provide details and photos of the item you found.',
                'order': 2
            },
            {
                'question': 'How do I claim an item?',
                'answer': 'Browse the listings, find your item, click on it and use the "Claim This Item" button. Provide proof of ownership.',
                'order': 3
            },
            {
                'question': 'Do I need to register to use the system?',
                'answer': 'Yes, you need to register with your university email to post reports or claim items. Browsing is available to everyone.',
                'order': 4
            },
            {
                'question': 'How long do items stay in the system?',
                'answer': 'Items remain in the system until they are claimed and returned, or marked as closed by the reporter.',
                'order': 5
            }
        ]
        
        for faq_data in faqs:
            FAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults={
                    'answer': faq_data['answer'],
                    'order': faq_data['order']
                }
            )
    
    def create_static_pages(self):
        self.stdout.write('Creating static pages...')
        pages = [
            {
                'slug': 'about',
                'title': 'About Lost & Found Portal',
                'content': '''
                <h2>Welcome to the University Lost & Found Portal</h2>
                <p>Our Lost & Found Portal is designed to help the university community recover lost items and return found items to their rightful owners.</p>
                
                <h3>How It Works</h3>
                <ul>
                    <li><strong>Report Lost Items:</strong> Create a detailed report with photos and location information</li>
                    <li><strong>Report Found Items:</strong> Post items you've found to help others locate their belongings</li>
                    <li><strong>Browse & Search:</strong> Look through listings to find your lost items</li>
                    <li><strong>Claim Items:</strong> Submit claims with proof of ownership</li>
                    <li><strong>Secure Communication:</strong> Message system for coordination</li>
                </ul>
                
                <h3>Features</h3>
                <ul>
                    <li>Photo uploads for better item identification</li>
                    <li>Location mapping and search</li>
                    <li>Category-based organization</li>
                    <li>Email notifications</li>
                    <li>QR code generation for physical tags</li>
                </ul>
                '''
            },
            {
                'slug': 'privacy',
                'title': 'Privacy Policy',
                'content': '''
                <h2>Privacy Policy</h2>
                <p><strong>Last updated:</strong> January 2024</p>
                
                <h3>Information We Collect</h3>
                <ul>
                    <li>Account information (name, email, student/staff ID)</li>
                    <li>Item reports and photos</li>
                    <li>Communication messages</li>
                    <li>Usage analytics</li>
                </ul>
                
                <h3>How We Use Information</h3>
                <ul>
                    <li>To facilitate lost and found matching</li>
                    <li>To enable communication between users</li>
                    <li>To improve our services</li>
                    <li>To send relevant notifications</li>
                </ul>
                
                <h3>Information Sharing</h3>
                <p>We do not sell personal information. Information is shared only as necessary to facilitate item returns within the university community.</p>
                
                <h3>Data Security</h3>
                <p>We implement appropriate security measures to protect your personal information.</p>
                '''
            },
            {
                'slug': 'terms',
                'title': 'Terms of Service',
                'content': '''
                <h2>Terms of Service</h2>
                <p><strong>Last updated:</strong> January 2024</p>
                
                <h3>Acceptable Use</h3>
                <ul>
                    <li>Use the service only for legitimate lost and found purposes</li>
                    <li>Provide accurate information in all reports</li>
                    <li>Respect other users and communicate professionally</li>
                    <li>Do not post inappropriate or offensive content</li>
                </ul>
                
                <h3>User Responsibilities</h3>
                <ul>
                    <li>Verify ownership before claiming items</li>
                    <li>Report any suspicious activity</li>
                    <li>Keep your account information current</li>
                    <li>Follow university policies and local laws</li>
                </ul>
                
                <h3>Prohibited Activities</h3>
                <ul>
                    <li>False claims or fraudulent reports</li>
                    <li>Harassment or abuse of other users</li>
                    <li>Commercial use of the platform</li>
                    <li>Attempts to circumvent security measures</li>
                </ul>
                
                <h3>Disclaimer</h3>
                <p>The university is not responsible for items lost or found, or for transactions between users.</p>
                '''
            }
        ]
        
        for page_data in pages:
            StaticPage.objects.get_or_create(
                slug=page_data['slug'],
                defaults={
                    'title': page_data['title'],
                    'content': page_data['content']
                }
            )
    
    def create_site_settings(self):
        self.stdout.write('Creating site settings...')
        settings = [
            {
                'key': 'site_name',
                'value': 'University Lost & Found Portal',
                'description': 'Main site name displayed in header'
            },
            {
                'key': 'contact_email',
                'value': 'lostfound@university.edu',
                'description': 'Contact email for support'
            },
            {
                'key': 'max_photos_per_report',
                'value': 5,
                'description': 'Maximum number of photos per report'
            },
            {
                'key': 'auto_approve_reports',
                'value': False,
                'description': 'Automatically approve new reports without moderation'
            },
            {
                'key': 'notification_email_enabled',
                'value': True,
                'description': 'Send email notifications to users'
            }
        ]
        
        for setting_data in settings:
            SiteSetting.objects.get_or_create(
                key=setting_data['key'],
                defaults={
                    'value': setting_data['value'],
                    'description': setting_data['description']
                }
            )
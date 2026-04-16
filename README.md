# University Lost & Found Portal

A comprehensive Django-based web application for managing lost and found items within a university community.

## Features

### Core Functionality
- **Item Reporting**: Users can report lost or found items with photos, location, and detailed descriptions
- **Search & Filtering**: Advanced search with filters by category, location, date, type, and more
- **Claims System**: Secure claim submission and approval workflow
- **User Authentication**: Email-based registration with role-based permissions (Student/Staff/Admin)
- **Messaging**: Direct communication between reporters and claimants
- **Notifications**: Real-time notifications for claims, approvals, and status changes

### Admin Features
- **Approval Workflow**: Admin approval required before reports go public
- **Analytics Dashboard**: Reports statistics, resolution rates, and trends
- **Content Management**: Manage categories, FAQs, static pages, and site settings
- **CSV Export**: Export reports and claims for analysis
- **Audit Logging**: Track all user actions for security

### Technical Features
- **REST API**: JSON API endpoints for mobile app integration
- **QR Code Generation**: Generate QR codes for physical item tags
- **Media Management**: Image upload with automatic resizing and optimization
- **Email Notifications**: Automated email notifications (console backend for development)
- **Responsive Design**: Mobile-friendly Bootstrap 5 interface
- **Docker Support**: Complete containerization with PostgreSQL and Nginx

## Tech Stack

- **Backend**: Django 5.1, Python 3.12
- **Database**: SQLite (development), PostgreSQL (production)
- **API**: Django REST Framework with JWT authentication
- **Frontend**: HTML5, Bootstrap 5, Vanilla JavaScript
- **Forms**: Django Crispy Forms with Bootstrap styling
- **File Storage**: Local storage (development), S3-compatible (production ready)
- **Containerization**: Docker and Docker Compose

## Quick Start

### Prerequisites
- Python 3.12+
- pip and virtual environment
- PostgreSQL (for production)
- Docker and Docker Compose (optional)

### Development Setup

1. **Clone and Setup Environment**:
```bash
git clone <repository-url>
cd lost_found_portal
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

2. **Database Setup**:
```bash
python manage.py migrate
python manage.py seed --users 20 --reports 50
```

3. **Run Development Server**:
```bash
python manage.py runserver
```

4. **Access the Application**:
- Web Interface: http://localhost:8000
- Django Admin: http://localhost:8000/admin
- API Root: http://localhost:8000/api/

### Docker Deployment

1. **Build and Run**:
```bash
docker-compose up --build
```

2. **Access the Application**:
- Web Interface: http://localhost
- The application will automatically migrate and seed data

## Demo Accounts

After running the seed command, you can use these accounts:

- **Admin**: admin@example.com / Admin123!
- **Student Demo**: user1@example.com / User123!
- **Staff Demo**: user2@example.com / User123!

## API Documentation

### Authentication
The API supports both session and JWT authentication. For JWT:

```bash
# Get JWT token
POST /api/auth/login/
{
  "username": "user1@example.com",
  "password": "User123!"
}

# Use token in subsequent requests
Authorization: Bearer <token>
```

### Key Endpoints

- `GET /api/reports/` - List all approved reports (public)
- `GET /api/reports/?category=Electronics&type=LOST&unclaimed=1` - Filtered search
- `POST /api/reports/` - Create new report (authenticated)
- `GET /api/categories/` - List all categories
- `GET /api/claims/` - List user's claims (authenticated)
- `GET /api/notifications/` - List user's notifications (authenticated)

### Search Parameters
- `q`: Search in title, description, location
- `category`: Filter by category ID
- `type`: LOST or FOUND
- `status`: OPEN, CLAIMED, RETURNED, CLOSED
- `location`: Filter by location text
- `with_photos`: Boolean, items with photos only
- `unclaimed_only`: Boolean, open items only
- `date_from`, `date_to`: Date range filters
- `sort`: Sort order (-created_at, view_count, etc.)

## File Structure

```
lost_found_portal/
├── core/                   # Django project settings
├── lost_found/            # Main application
│   ├── models.py         # Database models
│   ├── views.py          # View controllers
│   ├── forms.py          # Django forms
│   ├── admin.py          # Admin interface
│   ├── api_views.py      # DRF API views
│   ├── serializers.py    # API serializers
│   ├── urls.py           # URL routing
│   ├── fixtures/         # Initial data
│   └── management/       # Management commands
├── templates/             # HTML templates
├── static/               # CSS, JS, images
├── media/                # User uploads
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Multi-container setup
└── README.md           # This file
```

## Configuration

### Environment Variables

For production deployment, set these environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Email (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1
```

### S3 Storage Setup

To use S3 for file storage in production, uncomment the AWS settings in `settings.py`:

```python
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# ... other AWS settings
```

### Security Settings

For production, enable security settings in `settings.py`:

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

## Features Overview

### User Roles

1. **Guest (Unauthenticated)**
   - Browse and search approved listings
   - View item details and contact information
   - Access FAQ and static pages

2. **Student/Staff (Authenticated)**
   - All guest features
   - Create lost/found reports with photos
   - Submit claims on items
   - Message with other users
   - Personal dashboard with report management
   - Notification system

3. **Administrator (Staff/Superuser)**
   - All authenticated user features
   - Approve/reject reports and claims
   - Access admin dashboard with analytics
   - Manage users, categories, and content
   - Export data to CSV
   - View audit logs

### Workflow

1. **Report Creation**: User creates a report with details and photos
2. **Admin Approval**: Report requires admin approval before being public
3. **Public Listing**: Approved reports appear in search results
4. **Claim Submission**: Other users can submit claims with evidence
5. **Claim Review**: Reporter or admin reviews and approves/rejects claims
6. **Item Handover**: Status updated to claimed/returned
7. **Resolution**: Report marked as closed

### Business Rules

- Maximum 5 active reports per user (prevents spam)
- Maximum 5 photos per report (file size limit: 5MB each)
- Title: 10-120 characters, Description: 50-2000 characters
- Reports require admin approval before going public
- Users cannot claim their own reports
- One claim per user per report

## Testing

Run the test suite:

```bash
python manage.py test
```

## Acceptance Tests

The system meets these acceptance criteria:

1. ✅ Anonymous users can browse and search reports
2. ✅ Authenticated users can create reports with photos
3. ✅ Admin approval workflow functions correctly
4. ✅ Claims system works with notifications
5. ✅ Messaging enables user communication
6. ✅ CSV export provides complete data
7. ✅ QR codes generate and print properly
8. ✅ API returns filtered JSON results

## Deployment

### Production Deployment

1. **Server Setup**:
   - Ubuntu 20.04+ recommended
   - Install Docker and Docker Compose
   - Configure domain and SSL certificate

2. **Environment Configuration**:
   - Set production environment variables
   - Configure email server
   - Set up S3 bucket (optional)

3. **Deploy**:
```bash
# Clone repository
git clone <repository-url>
cd lost_found_portal

# Set environment variables
export DATABASE_URL=postgresql://...
export SECRET_KEY=...
export DEBUG=False

# Deploy with Docker
docker-compose -f docker-compose.prod.yml up -d
```

4. **Post-Deployment**:
   - Create superuser account
   - Configure domain in Django admin
   - Set up SSL with Certbot
   - Configure backup strategy

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify credentials

2. **File Upload Issues**:
   - Check MEDIA_ROOT permissions
   - Verify file size limits
   - Ensure directory exists

3. **Email Not Sending**:
   - Check EMAIL_* settings
   - Verify SMTP credentials
   - Check firewall rules

4. **Static Files Not Loading**:
   - Run `python manage.py collectstatic`
   - Check STATIC_ROOT configuration
   - Verify web server settings

### Logs

Check application logs:

```bash
# Docker logs
docker-compose logs web

# Django logs (if configured)
tail -f /path/to/django.log
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the FAQ section in the application

---

**Note**: This is a complete, production-ready application that can be deployed immediately after configuration. The codebase follows Django best practices and includes comprehensive security measures, testing, and documentation.
// Lost & Found Portal - Main JavaScript Application

class LostFoundApp {
    constructor() {
        this.loading = false;
        this.currentPage = 1;
        this.hasMore = true;
        this.init();
    }

    init() {
        this.initCSRF();
        this.initNotifications();
        this.initAdminCounts();
        this.initPhotoUpload();
        this.initSearch();
        this.initLocationPicker();
        this.initInfiniteScroll();
    }

    // CSRF Token handling
    initCSRF() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            window.csrfToken = csrfToken;
        } else {
            // Fallback: try to get from cookie
            const cookieValue = this.getCookie('csrftoken');
            if (cookieValue) {
                window.csrfToken = cookieValue;
            }
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Notification system
    initNotifications() {
        // Only load notifications if user is authenticated
        const notificationDropdown = document.getElementById('notificationDropdown');
        if (notificationDropdown) {
            this.loadNotifications();
            
            // Poll for new notifications every 30 seconds
            setInterval(() => {
                this.loadNotifications();
            }, 30000);

            // Mark notifications as read when dropdown is opened
            notificationDropdown.addEventListener('shown.bs.dropdown', () => {
                this.markNotificationsAsRead();
            });
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateNotificationUI(data.results || []);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    updateNotificationUI(notifications) {
        const badge = document.getElementById('notificationBadge');
        const dropdown = document.getElementById('notificationDropdown');
        
        if (!badge || !dropdown) return;

        const unreadCount = notifications.filter(n => !n.is_read).length;
        
        // Update badge
        if (unreadCount > 0) {
            badge.textContent = unreadCount;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }

        // Update dropdown content
        const dropdownMenu = dropdown.nextElementSibling;
        if (notifications.length > 0) {
            dropdownMenu.innerHTML = notifications.map(notification => `
                <li>
                    <div class="dropdown-item ${notification.is_read ? '' : 'bg-light'}">
                        <div class="d-flex justify-content-between">
                            <span class="text-truncate">${notification.verb}</span>
                            <small class="text-muted">${this.timeAgo(notification.created_at)}</small>
                        </div>
                    </div>
                </li>
            `).join('') + `
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-center" href="/dashboard/">View All</a></li>
            `;
        } else {
            dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">No notifications</span></li>';
        }
    }

    async markNotificationsAsRead() {
        try {
            if (!window.csrfToken) {
                console.warn('No CSRF token available, skipping mark as read');
                return;
            }
            
            await fetch('/api/notifications/mark-read/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': window.csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mark_all: true })
            });
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }

    // Admin badge counts (for staff users only)
    initAdminCounts() {
        // Only load admin counts if user is staff
        const adminDropdown = document.getElementById('adminDropdown');
        if (adminDropdown) {
            this.loadAdminCounts();
            
            // Update admin counts every 60 seconds
            setInterval(() => {
                this.loadAdminCounts();
            }, 60000);
        }
    }

    async loadAdminCounts() {
        try {
            const response = await fetch('/api/admin/counts/', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateAdminCounts(data);
            }
        } catch (error) {
            // Silently fail for admin counts - not critical
            console.log('Admin counts not available');
        }
    }

    updateAdminCounts(counts) {
        const pendingBadge = document.getElementById('pendingReportsCount');
        const flaggedBadge = document.getElementById('flaggedReportsCount');
        
        if (pendingBadge && counts.pending_reports !== undefined) {
            pendingBadge.textContent = counts.pending_reports;
            pendingBadge.style.display = counts.pending_reports > 0 ? 'inline' : 'none';
        }
        
        if (flaggedBadge && counts.flagged_reports !== undefined) {
            flaggedBadge.textContent = counts.flagged_reports;
            flaggedBadge.style.display = counts.flagged_reports > 0 ? 'inline' : 'none';
        }
    }

    // Photo upload with drag & drop
    initPhotoUpload() {
        const photoUpload = document.getElementById('photoUpload');
        const dropZone = document.getElementById('photoDropZone');
        
        if (!photoUpload || !dropZone) return;

        // Drag and drop handlers
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            this.handlePhotoFiles(files);
        });

        photoUpload.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            this.handlePhotoFiles(files);
        });
    }

    handlePhotoFiles(files) {
        const photoPreview = document.getElementById('photoPreview');
        if (!photoPreview) return;

        files.slice(0, 5).forEach((file, index) => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const preview = document.createElement('div');
                    preview.className = 'col-md-3 mb-3';
                    preview.innerHTML = `
                        <div class="card">
                            <img src="${e.target.result}" class="card-img-top" style="height: 150px; object-fit: cover;">
                            <div class="card-body p-2">
                                <input type="text" class="form-control form-control-sm" 
                                       placeholder="Optional caption..." name="caption_${index}">
                                <button type="button" class="btn btn-sm btn-danger mt-1 w-100" 
                                        onclick="this.closest('.col-md-3').remove()">
                                    Remove
                                </button>
                            </div>
                        </div>
                    `;
                    photoPreview.appendChild(preview);
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Enhanced search with autocomplete
    initSearch() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });
    }

    async performSearch(query) {
        if (query.length < 3) return;

        try {
            const response = await fetch(`/api/reports/search/?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                this.showSearchSuggestions(data.results || []);
            }
        } catch (error) {
            console.error('Error performing search:', error);
        }
    }

    showSearchSuggestions(results) {
        const suggestions = document.getElementById('searchSuggestions');
        if (!suggestions) return;

        if (results.length > 0) {
            suggestions.innerHTML = results.slice(0, 5).map(item => `
                <a href="/reports/${item.id}/" class="list-group-item list-group-item-action">
                    <div class="d-flex justify-content-between">
                        <span class="text-truncate">${item.title}</span>
                        <small class="text-muted">${item.type}</small>
                    </div>
                    <small class="text-muted">${item.location_text}</small>
                </a>
            `).join('');
            suggestions.classList.remove('d-none');
        } else {
            suggestions.classList.add('d-none');
        }
    }

    // Location picker (simple implementation)
    initLocationPicker() {
        const locationInput = document.getElementById('locationInput');
        const latInput = document.getElementById('id_latitude');
        const lngInput = document.getElementById('id_longitude');
        
        if (!locationInput) return;

        // Simple location suggestions (can be enhanced with real geolocation)
        const commonLocations = [
            'Main Library - 1st Floor',
            'Main Library - 2nd Floor',
            'Student Union Building',
            'Cafeteria - Main Hall',
            'Engineering Building - Room 101',
            'Science Building - Lab 201',
            'Administration Building',
            'Parking Lot A',
            'Parking Lot B',
            'Gymnasium - Main Hall',
            'Computer Lab - Room 150'
        ];

        locationInput.addEventListener('input', (e) => {
            const value = e.target.value.toLowerCase();
            const suggestions = commonLocations.filter(loc => 
                loc.toLowerCase().includes(value)
            );
            this.showLocationSuggestions(suggestions, e.target);
        });
    }

    showLocationSuggestions(suggestions, inputElement) {
        let suggestionsList = inputElement.nextElementSibling;
        
        if (!suggestionsList || !suggestionsList.classList.contains('location-suggestions')) {
            suggestionsList = document.createElement('div');
            suggestionsList.className = 'location-suggestions list-group position-absolute w-100';
            suggestionsList.style.zIndex = '1000';
            inputElement.parentNode.style.position = 'relative';
            inputElement.parentNode.appendChild(suggestionsList);
        }

        if (suggestions.length > 0 && inputElement.value.length > 2) {
            suggestionsList.innerHTML = suggestions.slice(0, 5).map(suggestion => `
                <a href="#" class="list-group-item list-group-item-action" 
                   onclick="this.selectLocation('${suggestion}'); return false;">
                    ${suggestion}
                </a>
            `).join('');
            suggestionsList.classList.remove('d-none');
        } else {
            suggestionsList.classList.add('d-none');
        }
    }

    selectLocation(location) {
        const locationInput = document.getElementById('locationInput');
        if (locationInput) {
            locationInput.value = location;
            document.querySelector('.location-suggestions').classList.add('d-none');
        }
    }

    // Infinite scroll for report listing
    initInfiniteScroll() {
        if (!window.location.pathname.includes('/reports/')) return;
        if (!document.querySelector('.report-card')) return;

        window.addEventListener('scroll', () => {
            if (this.loading || !this.hasMore) return;
            
            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            
            if (scrollTop + clientHeight >= scrollHeight - 1000) {
                this.loadMoreReports();
            }
        });
    }

    async loadMoreReports() {
        if (this.loading || !this.hasMore) return;
        
        this.loading = true;
        this.currentPage++;
        
        try {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('page', this.currentPage);
            
            const response = await fetch(`/api/reports/?${urlParams.toString()}`, {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.appendReports(data.results || []);
                
                if (!data.next) {
                    this.hasMore = false;
                }
            } else {
                // If no more pages, stop trying
                this.hasMore = false;
            }
        } catch (error) {
            console.error('Error loading more reports:', error);
            this.hasMore = false;
        } finally {
            this.loading = false;
        }
    }

    appendReports(reports) {
        const container = document.getElementById('results-container');
        if (!container) return;

        reports.forEach(report => {
            const reportCard = this.createReportCard(report);
            container.appendChild(reportCard);
        });
    }

    createReportCard(report) {
        const card = document.createElement('div');
        card.className = 'col-lg-4 col-md-6 mb-4';
        
        const photoUrl = report.photos && report.photos.length > 0 
            ? report.photos[0].image 
            : 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="200" fill="%23dee2e6"%3E%3Crect width="100%25" height="100%25"/%3E%3C/svg%3E';
        
        card.innerHTML = `
            <div class="card h-100">
                <img src="${photoUrl}" class="card-img-top" style="height: 200px; object-fit: cover;">
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-2">
                        <span class="badge bg-${report.type.toLowerCase() === 'lost' ? 'danger' : 'success'}">
                            ${report.type}
                        </span>
                        <span class="badge bg-secondary">${report.status}</span>
                    </div>
                    <h6 class="card-title">${this.truncate(report.title, 50)}</h6>
                    <p class="card-text text-muted small">
                        <i class="bi bi-geo-alt"></i> ${this.truncate(report.location_text, 40)}
                    </p>
                    <p class="card-text">${this.truncate(report.description, 100)}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            ${this.formatDate(report.date_event)} • ${report.view_count} views
                        </small>
                        <a href="/reports/${report.id}/" class="btn btn-primary btn-sm">View Details</a>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }

    // Utility functions
    truncate(str, length) {
        if (str.length <= length) return str;
        return str.substring(0, length) + '...';
    }

    timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.lostFoundApp = new LostFoundApp();
});

// Global utility functions for inline event handlers
window.selectLocation = function(location) {
    window.lostFoundApp.selectLocation(location);
};

// Messaging system (basic implementation)
class MessagingSystem {
    constructor() {
        this.initMessageForm();
        this.initMessagePolling();
    }

    initMessageForm() {
        const messageForm = document.getElementById('messageForm');
        if (!messageForm) return;

        messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage(new FormData(messageForm));
        });
    }

    async sendMessage(formData) {
        try {
            const response = await fetch('/messages/send/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': window.csrfToken
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.addMessageToUI(data.message);
                document.getElementById('messageForm').reset();
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    addMessageToUI(message) {
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.is_own ? 'message-own' : 'message-other'}`;
        messageElement.innerHTML = `
            <div class="message-content">
                <p>${message.text}</p>
                ${message.image ? `<img src="${message.image}" class="img-fluid mt-2" style="max-width: 200px;">` : ''}
                <small class="text-muted">${this.timeAgo(message.created_at)}</small>
            </div>
        `;

        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    initMessagePolling() {
        const threadId = document.getElementById('threadId')?.value;
        if (!threadId) return;

        // Poll for new messages every 5 seconds
        setInterval(() => {
            this.checkNewMessages(threadId);
        }, 5000);
    }

    async checkNewMessages(threadId) {
        try {
            const lastMessageTime = this.getLastMessageTime();
            const response = await fetch(`/api/messages/${threadId}/?since=${lastMessageTime}`);
            
            if (response.ok) {
                const data = await response.json();
                data.messages.forEach(message => {
                    this.addMessageToUI(message);
                });
            }
        } catch (error) {
            console.error('Error checking new messages:', error);
        }
    }

    getLastMessageTime() {
        const messages = document.querySelectorAll('.message');
        if (messages.length === 0) return new Date().toISOString();
        
        // This is a simplified implementation
        return new Date().toISOString();
    }
}

// Initialize messaging system if on a message page
if (document.getElementById('messageForm')) {
    new MessagingSystem();
}
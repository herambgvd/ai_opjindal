from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Enhanced User model with additional profile fields"""

    # Core fields
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Profile fields
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)

    # Preferences
    timezone = models.CharField(
        max_length=50,
        default='Asia/Kolkata',
        help_text="User's preferred timezone"
    )
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )
    language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('hi', 'Hindi')],
        default='en'
    )

    # Email preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications"
    )
    security_alerts = models.BooleanField(
        default=True,
        help_text="Receive security-related emails"
    )

    # Account status
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)

    # Tracking fields
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    def get_full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def get_short_name(self):
        """Return the short name of the user"""
        return self.first_name or self.username

    def get_initials(self):
        """Return user initials for avatar placeholder"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['created_at']),
        ]


class UserActivity(models.Model):
    """Track user activities for security and analytics"""

    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
        ('settings_change', 'Settings Change'),
        ('failed_login', 'Failed Login'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['timestamp']),
        ]


class UserPreferences(models.Model):
    """Extended user preferences and settings"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences'
    )

    # Dashboard preferences
    default_dashboard = models.CharField(
        max_length=50,
        choices=[
            ('cross_counting', 'Cross Counting Dashboard'),
            ('analytics', 'Analytics Dashboard'),
            ('overview', 'Overview Dashboard'),
        ],
        default='cross_counting'
    )

    # Notification preferences
    browser_notifications = models.BooleanField(default=True)
    sound_notifications = models.BooleanField(default=False)
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
        ],
        default='immediate'
    )

    # Data preferences
    data_retention_days = models.PositiveIntegerField(
        default=90,
        help_text="Number of days to retain user data"
    )
    export_format = models.CharField(
        max_length=10,
        choices=[('csv', 'CSV'), ('excel', 'Excel'), ('json', 'JSON')],
        default='csv'
    )

    # UI preferences
    items_per_page = models.PositiveIntegerField(default=25)
    show_animations = models.BooleanField(default=True)
    compact_mode = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Preferences"

    class Meta:
        verbose_name_plural = "User Preferences"
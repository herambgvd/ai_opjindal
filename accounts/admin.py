from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserActivity, UserPreferences


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with additional fields"""

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified', 'theme', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)

    # Fieldsets for the user edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('phone', 'avatar', 'bio')
        }),
        ('Preferences', {
            'fields': ('timezone', 'theme', 'language')
        }),
        ('Notification Settings', {
            'fields': ('email_notifications', 'security_alerts')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_token')
        }),
        ('Tracking', {
            'fields': ('last_login_ip',),
            'classes': ('collapse',)
        }),
    )

    # Fields for the add user form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # editing an existing object
            return readonly_fields + ('verification_token', 'last_login_ip')
        return readonly_fields


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity admin interface"""

    list_display = ('user', 'activity_type', 'description', 'ip_address', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address')
    readonly_fields = ('user', 'activity_type', 'description', 'ip_address', 'user_agent', 'timestamp', 'metadata')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False  # Don't allow manual creation of activities

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing of activities


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    """User preferences admin interface"""

    list_display = ('user', 'default_dashboard', 'notification_frequency', 'items_per_page', 'created_at')
    list_filter = ('default_dashboard', 'notification_frequency', 'browser_notifications', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Dashboard Preferences', {
            'fields': ('default_dashboard', 'items_per_page', 'compact_mode', 'show_animations')
        }),
        ('Notification Preferences', {
            'fields': ('browser_notifications', 'sound_notifications', 'notification_frequency')
        }),
        ('Data Preferences', {
            'fields': ('data_retention_days', 'export_format')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
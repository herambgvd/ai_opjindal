import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, UpdateView

from .forms import (
    UserRegistrationForm, CustomLoginForm, UserProfileForm,
    UserPreferencesForm, UserSettingsForm, CustomPasswordResetForm,
    CustomSetPasswordForm, CustomPasswordChangeForm
)
from .models import User, UserActivity, UserPreferences


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_activity(user, activity_type, description="", request=None, metadata=None):
    """Log user activity"""
    ip_address = get_client_ip(request) if request else None
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''

    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )


class LandingPageView(TemplateView):
    """Landing page for non-authenticated users"""
    template_name = 'accounts/landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('cross_counting:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    """Enhanced login view with activity logging"""
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)

        # Log successful login
        log_user_activity(
            user=user,
            activity_type='login',
            description='User logged in successfully',
            request=self.request
        )

        # Update last login IP
        user.last_login_ip = get_client_ip(self.request)
        user.save(update_fields=['last_login_ip'])

        # Handle remember me
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)

        messages.success(self.request, f'Welcome back, {user.get_short_name()}!')
        return super().form_valid(form)

    def form_invalid(self, form):
        # Log failed login attempt
        login_attempt = form.cleaned_data.get('login', '')
        if login_attempt:
            try:
                if '@' in login_attempt:
                    user = User.objects.get(email=login_attempt)
                else:
                    user = User.objects.get(username=login_attempt)

                log_user_activity(
                    user=user,
                    activity_type='failed_login',
                    description='Failed login attempt',
                    request=self.request
                )
            except User.DoesNotExist:
                pass

        return super().form_invalid(form)


def register_view(request):
    """Enhanced registration view"""
    if request.user.is_authenticated:
        return redirect('cross_counting:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create user preferences
            UserPreferences.objects.create(user=user)

            # Log registration
            log_user_activity(
                user=user,
                activity_type='registration',
                description='User registered successfully',
                request=request
            )

            # Auto login after registration
            login(request, user)
            messages.success(request, f'Welcome to Clarify, {user.get_short_name()}!')
            return redirect('cross_counting:dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_view(request):
    """User account dashboard"""
    user = request.user
    recent_activities = UserActivity.objects.filter(user=user)[:10]

    context = {
        'user': user,
        'recent_activities': recent_activities,
    }
    return render(request, 'accounts/dashboard.html', context)


@method_decorator(login_required, name='dispatch')
class ProfileView(UpdateView):
    """User profile management view"""
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log profile update
        log_user_activity(
            user=self.request.user,
            activity_type='profile_update',
            description='Profile updated successfully',
            request=self.request
        )

        messages.success(self.request, 'Profile updated successfully!')
        return response


@method_decorator(login_required, name='dispatch')
class PreferencesView(UpdateView):
    """User preferences management view"""
    model = UserPreferences
    form_class = UserPreferencesForm
    template_name = 'accounts/preferences.html'
    success_url = reverse_lazy('accounts:preferences')

    def get_object(self):
        preferences, created = UserPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log preferences update
        log_user_activity(
            user=self.request.user,
            activity_type='settings_change',
            description='Preferences updated successfully',
            request=self.request
        )

        messages.success(self.request, 'Preferences updated successfully!')
        return response


@method_decorator(login_required, name='dispatch')
class SettingsView(UpdateView):
    """User account settings view"""
    model = User
    form_class = UserSettingsForm
    template_name = 'accounts/settings.html'
    success_url = reverse_lazy('accounts:settings')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log settings update
        log_user_activity(
            user=self.request.user,
            activity_type='settings_change',
            description='Account settings updated successfully',
            request=self.request
        )

        messages.success(self.request, 'Settings updated successfully!')
        return response


@login_required
def change_password_view(request):
    """Change password view"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()

            # Log password change
            log_user_activity(
                user=request.user,
                activity_type='password_change',
                description='Password changed successfully',
                request=request
            )

            messages.success(request, 'Your password has been changed successfully!')
            return redirect('accounts:settings')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def activity_view(request):
    """User activity history view"""
    activities = UserActivity.objects.filter(user=request.user)

    # Filter by activity type if specified
    activity_type = request.GET.get('type')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(activities, 25)
    page = request.GET.get('page')
    activities = paginator.get_page(page)

    context = {
        'activities': activities,
        'activity_types': UserActivity.ACTIVITY_TYPES,
        'current_filter': activity_type,
    }
    return render(request, 'accounts/activity.html', context)


class CustomPasswordResetView(PasswordResetView):
    """Enhanced password reset view"""
    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        # Log password reset request
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            log_user_activity(
                user=user,
                activity_type='password_reset',
                description='Password reset requested',
                request=self.request
            )
        except User.DoesNotExist:
            pass

        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Enhanced password reset confirm view"""
    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log password reset completion
        log_user_activity(
            user=form.user,
            activity_type='password_change',
            description='Password reset completed',
            request=self.request
        )

        messages.success(self.request, 'Your password has been reset successfully! You can now log in.')
        return response


# API Views for AJAX requests
@login_required
@require_http_methods(["GET"])
def get_user_stats(request):
    """Get user statistics for dashboard"""
    user = request.user

    stats = {
        'total_activities': UserActivity.objects.filter(user=user).count(),
        'recent_logins': UserActivity.objects.filter(
            user=user,
            activity_type='login'
        ).count(),
        'profile_updates': UserActivity.objects.filter(
            user=user,
            activity_type='profile_update'
        ).count(),
    }

    return JsonResponse(stats)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_theme(request):
    """Update user theme preference via AJAX"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')

        if theme in ['light', 'dark']:
            request.user.theme = theme
            request.user.save(update_fields=['theme'])

            # Log theme change
            log_user_activity(
                user=request.user,
                activity_type='settings_change',
                description=f'Theme changed to {theme}',
                request=request
            )

            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid theme'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

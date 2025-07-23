from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User, UserPreferences
import re


class BaseModelForm(forms.ModelForm):
    """Base form with consistent styling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                    'rows': 4
                })
            else:
                field.widget.attrs.update({
                    'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
                })


class UserRegistrationForm(UserCreationForm):
    """Enhanced user registration form"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+91 9876543210'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must accept the terms and conditions'}
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply base styling
        for field_name, field in self.fields.items():
            if field_name == 'terms_accepted':
                field.widget.attrs.update({
                    'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                })
            else:
                field.widget.attrs.update({
                    'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
                })

        # Custom help texts
        self.fields['username'].help_text = "Letters, digits and @/./+/-/_ only."
        self.fields['password1'].help_text = "At least 8 characters with letters and numbers."
        self.fields['password2'].help_text = "Enter the same password as before."

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and special characters
            phone = re.sub(r'[^\d+]', '', phone)
            if not re.match(r'^\+?[1-9]\d{9,14}$', phone):
                raise ValidationError("Enter a valid phone number.")
        return phone

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username.lower()


class CustomLoginForm(forms.Form):
    """Enhanced login form with email or username"""

    login = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        login = self.cleaned_data.get('login')
        password = self.cleaned_data.get('password')

        if login and password:
            # Try to authenticate with username or email
            if '@' in login:
                try:
                    user = User.objects.get(email=login)
                    login = user.username
                except User.DoesNotExist:
                    pass

            self.user_cache = authenticate(
                self.request,
                username=login,
                password=password
            )

            if self.user_cache is None:
                raise ValidationError("Invalid username/email or password.")

            if not self.user_cache.is_active:
                raise ValidationError("This account is inactive.")

        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class UserProfileForm(BaseModelForm):
    """User profile update form"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 9876543210'}),
            'bio': forms.Textarea(attrs={'placeholder': 'Tell us about yourself...', 'rows': 4}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower()


class UserPreferencesForm(BaseModelForm):
    """User preferences form"""

    class Meta:
        model = UserPreferences
        fields = [
            'default_dashboard', 'browser_notifications', 'sound_notifications',
            'notification_frequency', 'items_per_page', 'show_animations',
            'compact_mode', 'export_format'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group fields for better organization
        self.field_groups = {
            'Dashboard': ['default_dashboard', 'items_per_page', 'compact_mode', 'show_animations'],
            'Notifications': ['browser_notifications', 'sound_notifications', 'notification_frequency'],
            'Data': ['export_format'],
        }


class UserSettingsForm(BaseModelForm):
    """User account settings form"""

    class Meta:
        model = User
        fields = ['timezone', 'theme', 'language', 'email_notifications', 'security_alerts']


class CustomPasswordResetForm(PasswordResetForm):
    """Enhanced password reset form"""

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Enter your email address',
            'autofocus': True
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Enhanced set password form"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            })


class CustomPasswordChangeForm(PasswordChangeForm):
    """Enhanced password change form"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            })

        self.fields['old_password'].widget.attrs['placeholder'] = 'Current Password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New Password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm New Password'
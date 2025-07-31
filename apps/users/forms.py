import logging

import requests
from allauth.account.forms import LoginForm, ChangePasswordForm, ResetPasswordForm, ResetPasswordKeyForm, \
    SetPasswordForm, SignupForm
from apps.utils.timezones import get_timezones_display
from django import forms
from django.conf import settings
from django.contrib.auth import forms as admin_forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .helpers import validate_profile_picture
from .models import CustomUser


class TurnstileSignupForm(SignupForm):
    """
    Sign up form that includes a turnstile captcha.
    """

    turnstile_token = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_turnstile_token(self):
        if not settings.TURNSTILE_SECRET:
            logging.info("No turnstile secret found, not checking captcha")
            return

        turnstile_token = self.cleaned_data.get("turnstile_token", None)
        if not turnstile_token:
            raise forms.ValidationError("Missing captcha. Please try again.")

        turnstile_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        payload = {
            "secret": settings.TURNSTILE_SECRET,
            "response": turnstile_token,
        }
        response = requests.post(turnstile_url, data=payload).json()
        if not response["success"]:
            raise forms.ValidationError("Invalid captcha. Please try again.")

        return turnstile_token


class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(label=gettext("Email"), required=True)
    language = forms.ChoiceField(label=gettext("Language"))
    timezone = forms.ChoiceField(label=gettext("Timezone"), required=False)

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "language", "timezone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        timezone = self.fields.get("timezone")
        timezone.choices = get_timezones_display()
        if settings.USE_I18N and len(settings.LANGUAGES) > 1:
            language = self.fields.get("language")
            language.choices = settings.LANGUAGES
        else:
            self.fields.pop("language")


class UploadAvatarForm(forms.Form):
    avatar = forms.FileField(validators=[validate_profile_picture])


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = CustomUser


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = CustomUser
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize the login field
        self.fields['login'].widget = forms.TextInput(
            attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Email or Username',
                'id': 'mail',
                'autocomplete': 'username',
            }
        )

        # Customize the password field
        self.fields['password'].widget = forms.PasswordInput(
            attrs={
                'class': 'form-control mb-2 position-relative',
                'placeholder': 'Enter Password',
                'id': 'password',
                'autocomplete': 'current-password',
            }
        )

        # Check if 'remember' exists before customizing
        if 'remember' in self.fields:
            self.fields['remember'].widget = forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            )


class PasswordChangeForm(ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(*args, **kwargs)
        # self.helper = FormHelper(self)

        self.fields['oldpassword'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter currunt password', 'id': 'password3'})
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter new password', 'id': 'password4'})
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter confirm password', 'id': 'password5'})
        self.fields['oldpassword'].label = "Currunt Password"
        self.fields['password2'].label = "Confirm Password"


class PasswordResetForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)
        # self.helper = FormHelper(self)

        self.fields['email'].widget = forms.EmailInput(
            attrs={'class': 'form-control mb-2', 'placeholder': ' Enter Email', 'id': 'email1'})
        self.fields['email'].label = "Email"


class PasswordResetKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super(PasswordResetKeyForm, self).__init__(*args, **kwargs)
        # self.helper = FormHelper(self)
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter new password', 'id': 'password6'})
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter confirm password', 'id': 'password7'})
        self.fields['password2'].label = "Confirm Password"


class PasswordSetForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(PasswordSetForm, self).__init__(*args, **kwargs)
        # self.helper = FormHelper(self)
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control mb-2', 'placeholder': 'Enter new password', 'id': 'password8'})
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Enter confirm password', 'id': 'password9'})
        self.fields['password2'].label = "Confirm Password"


class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']


class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    is_active = forms.BooleanField(required=False, initial=True)
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = ("name", "email", "password1", "password2", "is_active", "groups")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_active = self.cleaned_data["is_active"]
        if commit:
            user.save()
            user.groups.set(self.cleaned_data["groups"])
        return user


class CustomUserUpdateForm(UserChangeForm):
    password = None  # Hides the password field
    name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    is_active = forms.BooleanField(required=False)
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = ("name", "email", "is_active", "groups")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.name = self.cleaned_data["name"]
        user.is_active = self.cleaned_data["is_active"]
        if commit:
            user.save()
            user.groups.set(self.cleaned_data["groups"])
        return user


class TermsSignupForm(TurnstileSignupForm):
    """Custom signup form to add a checkbox for accepting the terms."""

    terms_agreement = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # blank out overly-verbose help text
        self.fields["password1"].help_text = ""
        link = '<a href="{}" target="_blank">{}</a>'.format(
            reverse("web:terms"),
            _("Terms and Conditions"),
        )
        self.fields["terms_agreement"].label = mark_safe(_("I agree to the {terms_link}").format(terms_link=link))

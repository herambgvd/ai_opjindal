from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from .forms import UserRegisterForm, CustomPasswordResetForm, CustomSetPasswordForm
from django.urls import reverse

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('cross_counting:dashboard')  # Redirect to cross_counting dashboard
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def dashboard(request):
    return redirect('cross_counting:dashboard')  # Redirect to cross_counting dashboard

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'accounts/password_reset_email.html'
    success_url = '/password_reset/done/'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = '/login/'
from django.urls import path
from django.contrib.auth.views import LogoutView, PasswordResetDoneView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Landing page
    path('', views.LandingPageView.as_view(), name='landing'),

    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', LogoutView.as_view(next_page='accounts:landing'), name='logout'),

    # Password management
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', views.change_password_view, name='change_password'),

    # User dashboard and profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('preferences/', views.PreferencesView.as_view(), name='preferences'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('activity/', views.activity_view, name='activity'),

    # API endpoints
    path('api/stats/', views.get_user_stats, name='api_stats'),
    path('api/theme/', views.update_theme, name='api_theme'),
]
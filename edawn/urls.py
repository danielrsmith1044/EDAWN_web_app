from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from core.ratelimit import ratelimit

# Rate-limit login: 5 attempts per IP per 5 minutes
_login_view = ratelimit(max_attempts=5, window=300, key_prefix='login')(
    auth_views.LoginView.as_view(template_name='registration/login.html')
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', _login_view, name='login'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.txt',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('', include('core.urls')),
]

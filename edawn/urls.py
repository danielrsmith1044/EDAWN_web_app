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
    path('', include('core.urls')),
]

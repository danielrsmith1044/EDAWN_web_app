"""
Simple per-IP rate limiting using Django's cache framework.

No external dependencies — uses the default cache backend (LocMemCache in dev).
"""

from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseForbidden


def ratelimit(max_attempts=5, window=300, key_prefix='rl'):
    """
    Decorator that limits POST requests per IP address.

    Args:
        max_attempts: Maximum POSTs allowed within the window.
        window: Time window in seconds (default 5 minutes).
        key_prefix: Cache key prefix to separate different endpoints.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            ip = _get_client_ip(request)
            cache_key = f"{key_prefix}:{ip}"
            attempts = cache.get(cache_key, 0)

            if attempts >= max_attempts:
                return HttpResponseForbidden(
                    "Too many attempts. Please try again later."
                )

            cache.set(cache_key, attempts + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')

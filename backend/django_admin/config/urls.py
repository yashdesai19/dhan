"""URL configuration for DHAN Admin project."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def admin_health(request):
    """Simple health endpoint for the Django Admin service."""
    return JsonResponse({"status": "ok", "service": "django_admin"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", admin_health, name="health"),
]

# Customize Admin Site Headers
admin.site.site_header = "DHAN Financial Platform Administration"
admin.site.site_title = "DHAN Admin"
admin.site.index_title = "System Management & Monitoring"

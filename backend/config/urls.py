from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def handler404(request, exception=None):
    return JsonResponse(
        {"error": {"code": "not_found", "message": "The requested resource was not found."}},
        status=404,
    )


def handler500(request):
    return JsonResponse(
        {"error": {"code": "server_error", "message": "An unexpected error occurred."}},
        status=500,
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(("apps.users.urls", "users"), namespace="v1")),
    path("api/v1/", include("apps.users.admin_urls")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.privacy.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.issues.urls")),
    path("api/v1/", include("apps.subscriptions.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.buyers.urls")),
    path("api/v1/", include("apps.payments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

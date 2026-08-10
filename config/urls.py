from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


# =========================
# CUSTOM DJANGO ADMIN NAME
# =========================

admin.site.site_header = "Barangay Maniwaya"
admin.site.site_title = "Barangay Maniwaya Admin Portal"
admin.site.index_title = "Barangay Management System"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

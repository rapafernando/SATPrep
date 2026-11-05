from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.APP_NAME} admin"
admin.site.site_title = f"{settings.APP_NAME} admin"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("core.urls")),
    path("", include("learn.urls")),
]

from django.conf import settings

from .ads import ads_visible_for
from .models import SiteSettings


def site(request):
    site_settings = SiteSettings.load()
    return {
        "APP_NAME": settings.APP_NAME,
        "APP_VERSION": settings.APP_VERSION,
        "admin_path": settings.ADMIN_URL,
        "site": site_settings,
        "show_ads": ads_visible_for(getattr(request, "user", None), site_settings),
    }

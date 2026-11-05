import json

from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

THEME_COLOR = "#3438D1"
BACKGROUND_COLOR = "#F4F5FB"


@require_GET
def manifest(request):
    """Web app manifest: this is what lets phones 'install' the site as an app icon."""
    data = {
        "id": "/",
        "name": settings.APP_NAME,
        "short_name": settings.APP_NAME[:12],
        "description": "Daily practice that builds toward your target score.",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": BACKGROUND_COLOR,
        "theme_color": THEME_COLOR,
        "icons": [
            {"src": static("icons/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    response = HttpResponse(json.dumps(data), content_type="application/manifest+json")
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
def service_worker(request):
    """Served from the site root so it can control every page."""
    response = render(request, "core/sw.js", content_type="application/javascript")
    response["Cache-Control"] = "no-cache"
    response["Service-Worker-Allowed"] = "/"
    return response


@require_GET
def offline(request):
    return render(request, "core/offline.html")


@require_GET
def install_help(request):
    return render(request, "core/install.html")


@require_GET
def robots(request):
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


@never_cache
@require_GET
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001
        return JsonResponse({"status": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def csrf_failed(request, reason=""):
    """A form was sent with an old or missing security token (phone slept, cookies cleared, session ended).

    Say so in plain words and send the person somewhere useful instead of a bare 403 page.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.utils.http import url_has_allowed_host_and_scheme

    if not request.user.is_authenticated:
        messages.error(request, "Your session ended. Please sign in again.")
        return redirect("login")
    messages.error(request, "That page was out of date, so nothing was saved. Please try again.")
    back = request.META.get("HTTP_REFERER", "")
    if back and url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        return redirect(back)
    return redirect("home")

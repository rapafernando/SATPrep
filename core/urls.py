from django.urls import path

from . import console, views

urlpatterns = [
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
    path("install/", views.install_help, name="install_help"),
    path("robots.txt", views.robots, name="robots"),
    path("healthz", views.healthz, name="healthz"),
    path("design/", console.design, name="design"),
    path("console/", console.dashboard, name="console"),
    path("console/approvals/", console.approvals, name="console_approvals"),
    path("console/members/", console.members, name="console_members"),
    path("console/settings/", console.ad_settings, name="console_settings"),
    path("console/users/<uuid:user_id>/action/", console.user_action, name="console_user_action"),
]

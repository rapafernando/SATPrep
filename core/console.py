"""The admin console: a phone-friendly page for the owner to approve members and manage ads.

Only staff accounts can open it. (The full Django admin at /admin/ stays available for content.)
"""
import json
import secrets
from functools import wraps

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import User

from .models import SiteSettings


def staff_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


@staff_required
def dashboard(request):
    counts = User.objects.aggregate(
        pending=Count("id", filter=Q(approval_status="pending")),
        approved=Count("id", filter=Q(approval_status="approved")),
        ad_free=Count("id", filter=Q(approval_status="approved", ad_free=True)),
    )
    return render(request, "console/dashboard.html", {"counts": counts, "site_settings": SiteSettings.load()})


@staff_required
def approvals(request):
    pending = User.objects.filter(approval_status="pending").order_by("date_joined")
    return render(request, "console/approvals.html", {"pending": pending})


@staff_required
def members(request):
    people = User.objects.exclude(approval_status="pending").order_by("approval_status", "username")
    return render(request, "console/members.html", {"people": people})


ACTIONS = {"approve", "reject", "revoke", "ad_free_on", "ad_free_off", "reset_password"}


@staff_required
@require_POST
def user_action(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get("action", "")
    if action not in ACTIONS:
        raise PermissionDenied
    if target == request.user and action in {"reject", "revoke"}:
        messages.error(request, "You cannot remove your own access.")
    elif action == "approve":
        target.approve(by=request.user)
        messages.success(request, f"Approved {target.name}.")
    elif action in {"reject", "revoke"}:
        target.reject()
        messages.success(request, f"Removed access for {target.name}.")
    elif action == "reset_password":
        if target.is_superuser and target != request.user:
            messages.error(request, "Change another admin's password in the Django admin instead.")
        else:
            temporary = secrets.token_urlsafe(9)
            target.set_password(temporary)  # also signs them out everywhere
            target.save(update_fields=["password", "updated_at"])
            messages.success(
                request,
                f"New password for {target.name}: {temporary}  (shown once. Tell them to change it under Me > Change password.)",
            )
    elif action in {"ad_free_on", "ad_free_off"}:
        target.ad_free = action == "ad_free_on"
        target.save(update_fields=["ad_free", "updated_at"])
        state = "ad-free" if target.ad_free else "will see ads (when ads are on)"
        messages.success(request, f"{target.name} is now {state}.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("console_approvals")


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["signups_open", "ads_enabled", "ad_label", "ad_html"]
        labels = {
            "signups_open": "Allow new people to sign up",
            "ads_enabled": "Show ads to members who are not ad-free",
            "ad_label": "Label shown above ads",
            "ad_html": "Ad code",
        }
        widgets = {"ad_html": forms.Textarea(attrs={"rows": 6, "spellcheck": "false"})}


@staff_required
def ad_settings(request):
    site_settings = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=site_settings)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved.")
        return redirect("console_settings")
    return render(request, "console/settings.html", {"form": form})


@staff_required
def design(request):
    """Every component in every state, for checking the design system by eye."""
    tokens = json.loads((settings.BASE_DIR / "replica" / "design" / "tokens.json").read_text(encoding="utf-8"))
    return render(request, "core/design.html", {"colors": list(tokens["color"].items()), "types": list(tokens["type"].items())})

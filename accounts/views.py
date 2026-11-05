from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from core.models import SiteSettings

from .forms import DeleteAccountForm, LoginForm, SignupForm
from .models import User
from .sessions import end_all_sessions

SIGNUPS_PER_HOUR = 5


def client_ip(request):
    # Caddy overwrites X-Forwarded-For with the real visitor address.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class LoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if not SiteSettings.load().signups_open:
        return render(request, "accounts/signup_closed.html")

    form = SignupForm(request.POST or None)
    if request.method == "POST":
        key = f"signup:{client_ip(request)}"
        count = cache.get(key, 0)
        if count >= SIGNUPS_PER_HOUR:
            form.add_error(None, "Too many sign-up attempts from this network. Try again in an hour.")
        elif form.is_valid():
            form.save()
            cache.set(key, count + 1, 3600)
            return redirect("signup_done")
        else:
            cache.set(key, count + 1, 3600)
    return render(request, "accounts/signup.html", {"form": form})


def signup_done(request):
    return render(request, "accounts/signup_done.html")


@require_POST
def logout_view(request):
    return auth_views.LogoutView.as_view()(request)


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("me")

    def form_valid(self, form):
        response = super().form_valid(form)  # keeps this phone signed in
        # A changed password also ends every other session of this member (Django does this by itself).
        messages.success(self.request, "Password changed. Other phones were signed out.")
        return response


@login_required
@require_POST
def sign_out_everywhere(request):
    end_all_sessions(request.user)
    logout(request)
    messages.success(request, "You were signed out everywhere. Sign in again when you are ready.")
    return redirect("login")


@login_required
def delete_account(request):
    """Permanently deletes the member and everything they own (answers, goal, scores, family links)."""
    last_admin = request.user.is_superuser and not User.objects.filter(is_superuser=True).exclude(pk=request.user.pk).exists()
    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == "POST" and not last_admin and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account and all your practice data were deleted.")
        return redirect("login")
    return render(request, "accounts/delete_account.html", {"form": form, "last_admin": last_admin})


def privacy(request):
    return render(request, "accounts/privacy.html", {"settings_obj": SiteSettings.load()})

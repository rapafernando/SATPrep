from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class ApprovalMiddleware:
    """If someone is signed in but their approval was withdrawn, sign them out."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_approved:
            logout(request)
            messages.error(request, "Your account does not have access right now.")
            return redirect("login")
        return self.get_response(request)

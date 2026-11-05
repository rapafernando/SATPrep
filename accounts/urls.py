from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("password/", login_required(views.PasswordChangeView.as_view()), name="password_change"),
    path("signout-everywhere/", views.sign_out_everywhere, name="sign_out_everywhere"),
    path("delete-account/", views.delete_account, name="delete_account"),
    path("privacy/", views.privacy, name="privacy"),
    path("signup/done/", views.signup_done, name="signup_done"),
]

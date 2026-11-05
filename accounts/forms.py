from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(
        label="Password again", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    # Honeypot: real people never see or fill this in; simple bots do.
    website = forms.CharField(required=False, label="Leave this empty", widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = User
        fields = ["username", "display_name", "role", "email"]
        labels = {
            "username": "Username",
            "display_name": "First name or nickname",
            "role": "I am a",
            "email": "Email (optional)",
        }
        help_texts = {"username": "Letters, numbers and @/./+/-/_ only."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].required = True
        self.fields["email"].required = False
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autocapitalize": "none"})

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is taken. Try another.")
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise ValidationError("Something went wrong. Please try again.")
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords do not match.")
        elif p1:
            candidate = User(username=cleaned.get("username", ""), email=cleaned.get("email", ""))
            try:
                validate_password(p1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.approval_status = User.Approval.PENDING
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Normal login, plus a clear message for people who are not approved yet."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.approval_status == User.Approval.PENDING:
            raise ValidationError(
                "Your account is waiting for approval. You will be able to sign in once the admin approves it.",
                code="pending",
            )
        if user.approval_status == User.Approval.REJECTED:
            raise ValidationError("This account does not have access.", code="rejected")


class DeleteAccountForm(forms.Form):
    """Asks for the password so a borrowed, unlocked phone cannot delete someone's account."""

    password = forms.CharField(
        label="Your password", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise ValidationError("That password is not right.")
        return password

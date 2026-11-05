from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings

from .models import User

PW = "Correct-horse-battery-9"


def make_user(username, status="approved", **extra):
    user = User.objects.create_user(username=username, password=PW, display_name=username.title(), **extra)
    user.approval_status = status
    user.save()
    return user


class SignupTests(TestCase):
    def setUp(self):
        cache.clear()

    def data(self, **over):
        base = {
            "username": "sam", "display_name": "Sam", "role": "student", "email": "",
            "password1": PW, "password2": PW, "website": "",
        }
        base.update(over)
        return base

    def test_signup_creates_pending_user(self):
        r = self.client.post(reverse("signup"), self.data())
        self.assertRedirects(r, reverse("signup_done"))
        self.assertEqual(User.objects.get(username="sam").approval_status, "pending")

    def test_honeypot_blocks_bots(self):
        r = self.client.post(reverse("signup"), self.data(website="http://spam"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="sam").exists())

    def test_duplicate_username_any_case(self):
        make_user("sam")
        r = self.client.post(reverse("signup"), self.data(username="SAM"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.filter(username__iexact="sam").count(), 1)

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("signup"), self.data(password1="12345678", password2="12345678"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="sam").exists())

    def test_signups_can_be_closed(self):
        s = SiteSettings.load()
        s.signups_open = False
        s.save()
        r = self.client.get(reverse("signup"))
        self.assertTemplateUsed(r, "accounts/signup_closed.html")

    def test_rate_limit_per_ip(self):
        for i in range(5):
            self.client.post(reverse("signup"), self.data(username=f"kid{i}"), REMOTE_ADDR="9.9.9.9")
        r = self.client.post(reverse("signup"), self.data(username="kid99"), REMOTE_ADDR="9.9.9.9")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="kid99").exists())


class ApprovalTests(TestCase):
    def login(self, username):
        return self.client.post(reverse("login"), {"username": username, "password": PW})

    def test_pending_cannot_log_in(self):
        make_user("pat", status="pending")
        r = self.login("pat")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "waiting for approval")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_rejected_cannot_log_in(self):
        make_user("rex", status="rejected")
        r = self.login("rex")
        self.assertContains(r, "does not have access")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_approved_can_log_in(self):
        make_user("amy")
        r = self.login("amy")
        self.assertEqual(r.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_approval_then_login(self):
        u = make_user("zed", status="pending")
        self.login("zed")
        u.approve()
        self.assertEqual(self.login("zed").status_code, 302)

    def test_withdrawn_approval_logs_out_existing_session(self):
        u = make_user("lee")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("home")).status_code, 302)  # to onboarding, but allowed in
        u.reject()
        r = self.client.get(reverse("home"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        u = make_user("kim")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_superuser_is_auto_approved(self):
        admin = User.objects.create_superuser(username="boss", password=PW)
        self.assertTrue(admin.is_approved)

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])


class LoginMessageTests(TestCase):
    def test_wrong_password_message_has_no_raw_placeholders(self):
        make_user("sam")
        r = self.client.post(reverse("login"), {"username": "sam", "password": "nope-nope-12"})
        self.assertContains(r, "Please enter a correct username and password")
        self.assertNotContains(r, "%(")


class AccountSelfServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("kid")

    def sign_in(self, client=None):
        c = client or self.client
        c.force_login(self.user)
        return c

    def test_password_change_keeps_this_phone_and_ends_the_others(self):
        phone, laptop = self.client.__class__(), self.client.__class__()
        self.sign_in(phone)
        self.sign_in(laptop)
        r = phone.post(reverse("password_change"), {
            "old_password": PW, "new_password1": "A-brand-new-pass-77", "new_password2": "A-brand-new-pass-77"})
        self.assertRedirects(r, reverse("me"), fetch_redirect_response=False)
        self.assertEqual(phone.get(reverse("me")).status_code, 200)
        self.assertEqual(laptop.get(reverse("me")).status_code, 302)  # signed out
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A-brand-new-pass-77"))

    def test_password_change_rejects_wrong_old_and_weak_new(self):
        self.sign_in()
        r = self.client.post(reverse("password_change"), {
            "old_password": "nope", "new_password1": "A-brand-new-pass-77", "new_password2": "A-brand-new-pass-77"})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("password_change"), {
            "old_password": PW, "new_password1": "12345678", "new_password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PW))

    def test_sign_out_everywhere_only_touches_this_member(self):
        other = make_user("friend")
        phone, laptop, friend = self.client.__class__(), self.client.__class__(), self.client.__class__()
        self.sign_in(phone)
        self.sign_in(laptop)
        friend.force_login(other)
        phone.post(reverse("sign_out_everywhere"))
        self.assertEqual(phone.get(reverse("me")).status_code, 302)
        self.assertEqual(laptop.get(reverse("me")).status_code, 302)
        self.assertEqual(friend.get(reverse("me")).status_code, 200)

    def test_sign_out_everywhere_needs_post_and_login(self):
        self.assertEqual(self.client.post(reverse("sign_out_everywhere")).status_code, 302)
        self.sign_in()
        self.assertEqual(self.client.get(reverse("sign_out_everywhere")).status_code, 405)

    def test_delete_account_removes_everything_and_nothing_else(self):
        from learn.models import Attempt, Question, Skill

        other = make_user("friend")
        skill = Skill.objects.create(track="math", domain="Algebra", name="S", slug="s", order=1)
        q = Question.objects.create(skill=skill, stem="1+1?", answer_type="numeric", correct_answer="2", explanation="x")
        for u in (self.user, other):
            Attempt.objects.create(user=u, question=q, answer="2", is_correct=True)
        self.sign_in()
        bad = self.client.post(reverse("delete_account"), {"password": "wrong"})
        self.assertEqual(bad.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        r = self.client.post(reverse("delete_account"), {"password": PW})
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(Attempt.objects.filter(user=self.user_id_gone()).count(), 0)
        self.assertEqual(Attempt.objects.count(), 1)  # the friend's answer is untouched
        self.assertTrue(User.objects.filter(pk=other.pk).exists())

    def user_id_gone(self):
        return self.user.pk

    def test_last_admin_cannot_delete_themselves(self):
        admin = make_user("boss", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        r = self.client.post(reverse("delete_account"), {"password": PW})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(pk=admin.pk).exists())

    def test_privacy_page_is_public(self):
        r = self.client.get(reverse("privacy"))
        self.assertContains(r, "What is stored")
        self.assertContains(r, "Ads are currently off")

    def test_permissions_policy_header(self):
        self.assertIn("camera=()", self.client.get(reverse("login"))["Permissions-Policy"])

    def test_signup_rate_limit_uses_the_shared_cache(self):
        from django.conf import settings

        self.assertIn("DatabaseCache", settings.CACHES["default"]["BACKEND"])

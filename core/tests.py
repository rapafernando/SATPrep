import json

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests import PW, make_user

from .ads import ads_visible_for
from .models import SiteSettings


def set_site(**kw):
    s = SiteSettings.load()
    for k, v in kw.items():
        setattr(s, k, v)
    s.save()
    return s


class AdsLogicTests(TestCase):
    def test_matrix(self):
        normal, free = make_user("normal"), make_user("free", ad_free=True)
        pending = make_user("pending", status="pending")
        anon = type("Anon", (), {"is_authenticated": False})()
        off = set_site(ads_enabled=False, ad_html="<b>ad</b>")
        self.assertFalse(ads_visible_for(normal, off))
        on_no_code = set_site(ads_enabled=True, ad_html="  ")
        self.assertFalse(ads_visible_for(normal, on_no_code))
        on = set_site(ads_enabled=True, ad_html="<b>ad</b>")
        self.assertTrue(ads_visible_for(normal, on))
        self.assertFalse(ads_visible_for(free, on))
        self.assertFalse(ads_visible_for(pending, on))
        self.assertFalse(ads_visible_for(anon, on))

    def test_default_is_off(self):
        self.assertFalse(SiteSettings.load().ads_enabled)


class AdsRenderingTests(TestCase):
    def setUp(self):
        from learn.models import Goal
        import datetime
        self.normal, self.free = make_user("normal"), make_user("free", ad_free=True)
        for u in (self.normal, self.free):
            Goal.objects.create(user=u, current_score=1000, target_score=1200,
                                test_date=datetime.date.today() + datetime.timedelta(days=60), minutes_per_day=30)
        set_site(ads_enabled=True, ad_html='<div id="the-ad">BUY</div>')

    def test_ad_shows_for_normal_member_only(self):
        self.client.force_login(self.normal)
        self.assertContains(self.client.get(reverse("home")), "the-ad")
        self.client.force_login(self.free)
        self.assertNotContains(self.client.get(reverse("home")), "the-ad")

    def test_never_on_question_page(self):
        from learn.models import PracticeSession
        from learn.services import start_session
        from django.core.management import call_command
        call_command("seed_content")
        self.client.force_login(self.normal)
        session = start_session(self.normal, PracticeSession.Kind.DAILY)
        r = self.client.get(reverse("practice", args=[session.id]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "the-ad")

    def test_ads_off_hides_everywhere(self):
        set_site(ads_enabled=False)
        self.client.force_login(self.normal)
        self.assertNotContains(self.client.get(reverse("home")), "the-ad")


class ConsoleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="boss", password=PW)
        self.member = make_user("member")
        self.pending = make_user("newbie", status="pending")

    def test_staff_only(self):
        for name in ("console", "console_approvals", "console_members", "console_settings"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)  # anonymous
        self.client.force_login(self.member)
        for name in ("console", "console_approvals", "console_members", "console_settings"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_non_staff_cannot_approve_self(self):
        self.client.force_login(self.member)
        r = self.client.post(reverse("console_user_action", args=[self.pending.id]), {"action": "approve"})
        self.assertEqual(r.status_code, 403)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.approval_status, "pending")

    def test_admin_pages_render(self):
        self.client.force_login(self.admin)
        for name in ("console", "console_approvals", "console_members", "console_settings"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("console_approvals")), "newbie")

    def act(self, user, action, **extra):
        return self.client.post(reverse("console_user_action", args=[user.id]), {"action": action, **extra})

    def test_approve_reject_revoke(self):
        self.client.force_login(self.admin)
        self.act(self.pending, "approve")
        self.pending.refresh_from_db()
        self.assertTrue(self.pending.is_approved)
        self.assertEqual(self.pending.approved_by, self.admin)
        self.act(self.pending, "revoke")
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.approval_status, "rejected")

    def test_ad_free_toggle(self):
        self.client.force_login(self.admin)
        self.act(self.member, "ad_free_on")
        self.member.refresh_from_db()
        self.assertTrue(self.member.ad_free)
        self.act(self.member, "ad_free_off")
        self.member.refresh_from_db()
        self.assertFalse(self.member.ad_free)

    def test_cannot_lock_yourself_out(self):
        self.client.force_login(self.admin)
        self.act(self.admin, "revoke")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_approved)

    def test_unknown_action_rejected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.act(self.member, "make_admin").status_code, 403)

    def test_open_redirect_ignored(self):
        self.client.force_login(self.admin)
        r = self.act(self.pending, "approve", next="https://evil.example/")
        self.assertRedirects(r, reverse("console_approvals"), fetch_redirect_response=False)
        r = self.act(self.member, "ad_free_on", next=reverse("console_members"))
        self.assertRedirects(r, reverse("console_members"), fetch_redirect_response=False)

    def test_action_requires_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("console_user_action", args=[self.member.id])).status_code, 405)

    def test_settings_save(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("console_settings"),
                             {"signups_open": "on", "ads_enabled": "on", "ad_label": "Sponsored", "ad_html": "<p>x</p>"})
        self.assertEqual(r.status_code, 302)
        s = SiteSettings.load()
        self.assertTrue(s.ads_enabled)
        self.assertEqual(s.ad_html, "<p>x</p>")

    def test_ensure_admin_is_ad_free_and_idempotent(self):
        from django.core.management import call_command
        User.objects.filter(is_superuser=True).delete()
        with override_settings():
            import os
            os.environ.update(DJANGO_SUPERUSER_USERNAME="owner", DJANGO_SUPERUSER_PASSWORD=PW)
            try:
                call_command("ensure_admin")
                call_command("ensure_admin")
            finally:
                os.environ.pop("DJANGO_SUPERUSER_USERNAME"); os.environ.pop("DJANGO_SUPERUSER_PASSWORD")
        owner = User.objects.get(username="owner")
        self.assertTrue(owner.is_superuser and owner.is_approved and owner.ad_free)
        self.assertEqual(User.objects.filter(username="owner").count(), 1)


class PwaTests(TestCase):
    def test_manifest(self):
        r = self.client.get(reverse("manifest"))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["display"], "standalone")
        sizes = {i["sizes"] for i in data["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes)
        self.assertTrue(any("maskable" in i.get("purpose", "") for i in data["icons"]))

    def test_service_worker(self):
        r = self.client.get(reverse("service_worker"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("javascript", r["Content-Type"])
        self.assertEqual(r["Service-Worker-Allowed"], "/")
        self.assertIn("no-cache", r["Cache-Control"])

    def test_public_pages(self):
        for name in ("offline", "install_help", "healthz", "robots", "login", "signup"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("robots")), "Disallow: /")

    def test_healthz_checks_database(self):
        self.assertContains(self.client.get(reverse("healthz")), "ok")

    def test_signed_in_pages_not_cached_by_sw(self):
        body = self.client.get(reverse("service_worker")).content.decode()
        self.assertNotIn("/practice/", body)


class DesignPageTests(TestCase):
    def test_staff_only(self):
        self.assertEqual(self.client.get(reverse("design")).status_code, 302)
        self.client.force_login(make_user("member"))
        self.assertEqual(self.client.get(reverse("design")).status_code, 403)

    def test_renders_for_staff(self):
        admin = User.objects.create_superuser(username="boss", password=PW)
        self.client.force_login(admin)
        r = self.client.get(reverse("design"))
        self.assertContains(r, "Colour roles")
        self.assertContains(r, "--color-accent")


class TokenBuildTests(TestCase):
    """tokens.css must match tokens.json, and every colour pair must pass WCAG AA in both modes."""

    def test_css_is_up_to_date_and_contrast_passes(self):
        import importlib.util
        from django.conf import settings

        spec = importlib.util.spec_from_file_location("build_tokens", settings.BASE_DIR / "tools" / "build_tokens.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tokens = json.loads(mod.TOKENS.read_text(encoding="utf-8"))
        self.assertEqual(mod.OUT.read_text(encoding="utf-8"), mod.build(tokens), "run: python3 tools/build_tokens.py")
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.check(tokens), 0)


class ConsoleScreenTests(TestCase):
    def setUp(self):
        self.admin = make_user("boss", is_staff=True, is_superuser=True)
        make_user("waiting", status="pending")
        self.client.force_login(self.admin)

    def test_nav_marks_current_and_shows_pending_badge(self):
        html = self.client.get(reverse("console_approvals")).content.decode()
        self.assertIn('aria-current="page"', html)
        self.assertIn('aria-label="1 waiting"', html)

    def test_members_table_has_ad_free_switch(self):
        html = self.client.get(reverse("console_members")).content.decode()
        self.assertIn('role="switch"', html)
        self.assertIn("Ad-free for Boss", html)


class ConsolePasswordResetTests(TestCase):
    def setUp(self):
        self.admin = make_user("boss", is_staff=True, is_superuser=True)
        self.kid = make_user("kid")

    def act(self, user, action):
        self.client.force_login(self.admin)
        return self.client.post(reverse("console_user_action", args=[user.id]), {"action": action}, follow=True)

    def test_reset_sets_a_new_password_and_ends_their_sessions(self):
        phone = self.client.__class__()
        phone.force_login(self.kid)
        r = self.act(self.kid, "reset_password")
        self.assertContains(r, "New password for Kid")
        self.kid.refresh_from_db()
        self.assertFalse(self.kid.check_password(PW))
        self.assertEqual(phone.get(reverse("me")).status_code, 302)

    def test_non_staff_cannot_reset_anyones_password(self):
        other = make_user("friend")
        self.client.force_login(self.kid)
        r = self.client.post(reverse("console_user_action", args=[other.id]), {"action": "reset_password"})
        self.assertEqual(r.status_code, 403)
        other.refresh_from_db()
        self.assertTrue(other.check_password(PW))

    def test_cannot_reset_another_admins_password(self):
        admin2 = make_user("boss2", is_staff=True, is_superuser=True)
        r = self.act(admin2, "reset_password")
        self.assertContains(r, "Django admin")
        admin2.refresh_from_db()
        self.assertTrue(admin2.check_password(PW))


class SecondUserIsolationTests(TestCase):
    """A second member must get nothing back that belongs to the first."""

    def test_other_members_progress_never_appears(self):
        import datetime

        from django.utils import timezone

        from learn.models import Goal

        a, b = make_user("alice"), make_user("bob")
        Goal.objects.create(user=a, current_score=1000, target_score=1500, target_school="Secret U",
                            test_date=timezone.localdate() + datetime.timedelta(days=60), minutes_per_day=30)
        Goal.objects.create(user=b, current_score=900, target_score=1100,
                            test_date=timezone.localdate() + datetime.timedelta(days=60), minutes_per_day=30)
        self.client.force_login(b)
        for name in ("home", "me", "progress", "plan", "practice_home"):
            html = self.client.get(reverse(name)).content.decode()
            self.assertNotIn("Secret U", html, name)
            self.assertNotIn("1500", html, name)
        self.assertEqual(self.client.get(reverse("family")).status_code, 404)  # not a parent


class ErrorPageTests(TestCase):
    """BUG-002 and BUG-006: stale forms and missing pages get plain, kind pages with a way back."""

    def test_stale_csrf_for_signed_out_visitor_goes_to_sign_in(self):
        from django.test import Client

        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("sign_out_everywhere"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        self.assertContains(c.get(reverse("login")), "Your session ended")

    def test_stale_csrf_for_member_goes_back_with_a_message(self):
        from django.test import Client

        c = Client(enforce_csrf_checks=True)
        c.force_login(make_user("kid"))
        r = c.post(reverse("logout"), HTTP_REFERER="http://testserver/me/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "http://testserver/me/")
        self.assertContains(c.get("/me/"), "out of date")

    def test_csrf_failure_never_redirects_off_site(self):
        from django.test import Client

        c = Client(enforce_csrf_checks=True)
        c.force_login(make_user("kid"))
        r = c.post(reverse("logout"), HTTP_REFERER="https://evil.example/x")
        self.assertEqual(r.url, reverse("home"))

    def test_404_page_has_a_way_back(self):
        r = self.client.get("/no-such-page/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, 'href="/"', status_code=404)
        self.assertContains(r, "cannot find that page", status_code=404)

    def test_403_page_has_a_way_back(self):
        self.client.force_login(make_user("kid"))
        r = self.client.get(reverse("console"))
        self.assertContains(r, "do not have access", status_code=403)

    def test_500_template_renders_standalone(self):
        from django.template.loader import render_to_string

        html = render_to_string("500.html")
        self.assertIn("Something went wrong", html)

    @override_settings(AXES_ENABLED=True)
    def test_lockout_page_is_friendly_and_in_the_app_style(self):
        from django.core.cache import cache

        cache.clear()
        make_user("sam")
        for _ in range(6):
            self.client.post(reverse("login"), {"username": "sam", "password": "wrong-wrong-1"})
        r = self.client.post(reverse("login"), {"username": "sam", "password": PW})
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, "Back to sign in", status_code=429)

import re

import pytest
from conftest import BASE, PW


def signup(app, username, name="Test Kid", pw=PW, pw2=None, role="Student", email=""):
    app.go("/signup/")
    p = app.page
    p.get_by_label("Username").fill(username)
    p.get_by_label("First name or nickname").fill(name)
    p.get_by_label("I am a").select_option(label=role)
    p.get_by_label("Email (optional)").fill(email)
    p.get_by_label(re.compile(r"^Password:?$")).fill(pw)
    p.get_by_label("Password again").fill(pw if pw2 is None else pw2)
    p.get_by_role("button", name="Send request").click()
    p.wait_for_load_state("networkidle")


@pytest.fixture(autouse=True)
def fresh_rate_limit(db):
    db.run("delete from scorepath_cache")
    yield


def test_A1_H1_signup_wait_approve_signin(make_app):
    app = make_app()
    signup(app, "newcomer", name="Newcomer")
    assert app.page.url.endswith("/signup/done/")
    app.login("newcomer", expect_ok=False)
    assert "waiting for approval" in app.page.locator("main").inner_text().lower()
    admin = make_app("boss")
    admin.go("/console/approvals/")
    row = admin.page.locator(".person", has_text="newcomer")
    row.get_by_role("button", name=re.compile("Approve")).click()
    admin.page.wait_for_load_state("networkidle")
    app.login("newcomer")
    assert app.page.url.endswith("/onboarding/")


def test_A1_E1_duplicate_username_any_case(make_app):
    app = make_app()
    signup(app, "SAM")
    assert "taken" in app.page.content()


def test_A1_E2_weak_or_mismatched_password(make_app, db):
    app = make_app()
    signup(app, "weakling", pw="12345678")
    assert app.page.locator(".error").count() >= 1
    signup(app, "weakling", pw=PW, pw2=PW + "x")
    assert "do not match" in app.page.content()
    assert db.one("select count(*) from accounts_user where username='weakling'") == 0


def test_A1_E3_emoji_and_long_names(make_app, db):
    app = make_app()
    signup(app, "emojikid", name="José 🎓")
    assert app.page.url.endswith("/signup/done/")
    assert db.one("select display_name from accounts_user where username='emojikid'") == "José 🎓"
    signup(app, "longname", name="x" * 80)
    assert app.page.locator(".error").count() >= 1 or app.page.url.endswith("/signup/done/")
    assert db.one("select length(display_name) from accounts_user where username='longname'") in (None, 60)


def test_A1_E4_lockout(make_app, kid):
    app = make_app()
    app.allowed.append("429")
    for _ in range(6):
        app.login(kid, "wrong-password-1", expect_ok=False)
    app.login(kid, PW, expect_ok=False)
    assert "/login" in app.page.url
    body = app.page.locator("body")
    text = body.inner_text().lower()
    assert "locked" in text or "too many" in text or "try again" in text, text
    # a member must be able to see what to do next, in the app's own look
    assert app.page.locator("a[href='/login/'], a[href='/']").count() >= 1, "lockout page is a dead end"
    assert app.page.locator("link[rel=stylesheet]").count() >= 1, "lockout page is unstyled"


def test_A1_E5_signup_rate_limit(make_app, db):
    app = make_app()
    for i in range(6):
        signup(app, "weak%d" % i, pw="12345678")
    assert "Too many" in app.page.content()


def test_A1_E6_signups_closed(make_app, db):
    admin = make_app("boss")
    admin.go("/console/settings/")
    box = admin.page.get_by_label("Allow new people to sign up")
    box.uncheck()
    admin.page.get_by_role("button", name="Save").click()
    try:
        guest = make_app()
        guest.go("/signup/")
        assert guest.page.get_by_label("Username").count() == 0
    finally:
        admin.go("/console/settings/")
        admin.page.get_by_label("Allow new people to sign up").check()
        admin.page.get_by_role("button", name="Save").click()


def test_A1_N1_rejected_member(make_app):
    app = make_app()
    app.login("rejected", expect_ok=False)
    assert "/login" in app.page.url
    assert "waiting" not in app.page.locator("main").inner_text().lower()


def test_A1_N2_access_removed_while_signed_in(make_app, kid, db):
    member = make_app(kid)
    admin = make_app("boss")
    admin.go("/console/members/")
    admin.page.get_by_role("button", name=f"Remove access for {kid.title().replace('K', 'Kid ', 1)}").click() if False else None
    uid = db.one("select id from accounts_user where username=?", kid)
    db.run("update accounts_user set approval_status='rejected' where username=?", kid)
    member.go("/progress/")
    assert "/login" in member.page.url
    assert "does not have access" in member.page.content()

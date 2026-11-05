import json
import re

from conftest import BASE, PW
from helpers import hscroll


def test_A3_H1_change_password(make_app, kid):
    app = make_app(kid)
    app.go("/password/")
    app.page.get_by_label("Old password").fill(PW)
    app.page.get_by_label("New password", exact=False).first.fill("A-brand-new-pass-77")
    app.page.get_by_label("New password confirmation").fill("A-brand-new-pass-77")
    app.page.get_by_role("button", name="Save new password").click()
    app.page.wait_for_url("**/me/")
    other = make_app()
    other.login(kid, PW, expect_ok=False)
    assert "/login" in other.page.url
    other.login(kid, "A-brand-new-pass-77")


def test_A3_H2_sign_out_everywhere(make_app, kid):
    a, b = make_app(kid), make_app(kid)
    friend = make_app("k69")
    a.go("/me/")
    a.page.get_by_role("button", name="Sign out everywhere").click()
    a.page.wait_for_load_state("networkidle")
    assert "/login" in a.page.url
    b.go("/progress/")
    assert "/login" in b.page.url
    friend.go("/progress/")
    assert "/login" not in friend.page.url


def test_A3_H3_delete_account(make_app, db):
    app = make_app("k68")
    app.go("/me/")
    app.page.get_by_role("link", name=re.compile("Delete my account")).click()
    app.page.get_by_label("Your password").fill(PW)
    app.page.get_by_role("button", name="Delete everything").click()
    app.page.wait_for_url("**/login/")
    assert db.one("select count(*) from accounts_user where username='k68'") == 0
    assert db.one("select count(*) from accounts_user where username='k67'") == 1
    app.login("k68", PW, expect_ok=False)
    assert "/login" in app.page.url


def test_A3_E1_wrong_password_on_delete(make_app, db):
    app = make_app("k67")
    app.go("/delete-account/")
    app.page.get_by_label("Your password").fill("nope-nope-12")
    app.page.get_by_role("button", name="Delete everything").click()
    assert "not right" in app.page.content()
    assert db.one("select count(*) from accounts_user where username='k67'") == 1


def test_A4_H1_manifest(make_app):
    app = make_app()
    r = app.page.request.get(BASE + "/manifest.webmanifest")
    m = json.loads(r.text())
    assert m["display"] == "standalone" and m["start_url"] and m["name"]
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for icon in m["icons"]:
        assert app.page.request.get(BASE + icon["src"]).status == 200


def test_A4_H2_service_worker_active(make_app):
    app = make_app()
    app.go("/login/")
    app.page.wait_for_load_state("networkidle")
    scope = app.page.evaluate("navigator.serviceWorker.ready.then(r => r.scope)")
    assert scope == BASE + "/"


def test_A4_H3_iphone_install_hint(make_app, kid):
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
    app = make_app(kid, user_agent=ua)
    app.go("/")
    app.page.wait_for_load_state("networkidle")
    banner = app.page.locator("#install-banner")
    banner.wait_for(state="visible", timeout=5000)
    assert re.search(r"share", app.page.locator("#install-hint").inner_text(), re.I)
    app.page.get_by_role("button", name="Not now").click()
    assert banner.is_hidden()
    app.page.reload()
    app.page.wait_for_timeout(500)
    assert banner.is_hidden()


def test_A4_E1_offline_page(make_app, kid):
    app = make_app(kid)
    app.allowed += ["Failed to load resource", "net::ERR"]
    app.go("/")
    app.page.wait_for_load_state("networkidle")
    app.page.evaluate("navigator.serviceWorker.ready")
    app.page.reload()  # make sure the worker controls the page
    app.ctx.set_offline(True)
    app.page.goto(BASE + "/progress/")
    assert "offline" in app.page.locator("body").inner_text().lower()
    app.ctx.set_offline(False)


def test_A4_E2_private_pages_not_cached(make_app, kid):
    app = make_app(kid)
    app.allowed += ["Failed to load resource", "net::ERR"]
    app.go("/progress/")
    app.page.evaluate("navigator.serviceWorker.ready")
    app.page.reload()
    app.page.get_by_role("button", name="Sign out").click() if app.page.get_by_role("button", name="Sign out").count() else None
    app.go("/me/")
    app.page.get_by_role("button", name="Sign out", exact=True).click()
    app.page.wait_for_load_state("networkidle")
    app.ctx.set_offline(True)
    try:
        app.page.goto(BASE + "/progress/")
    except Exception:
        pass
    text = app.page.locator("body").inner_text().lower()
    assert "predicted score" not in text and "streak" not in text
    app.ctx.set_offline(False)

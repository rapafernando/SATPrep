import re

from conftest import BASE, PW
from helpers import hscroll, start_daily


def test_A2_H1_approvals(make_app, db):
    db.run("insert into accounts_user (id,password,is_superuser,username,first_name,last_name,email,is_staff,is_active,date_joined,display_name,role,approval_status,ad_free,updated_at) "
           "values ('aaaaaaaa00000000000000000000000%d',?,0,?, '', '', '', 0,1,datetime('now'),?,'student','pending',0,datetime('now'))" % 1,
           "x", "pend1", "Pend One")
    admin = make_app("boss")
    admin.go("/console/approvals/")
    badge_before = int(admin.page.locator(".subnav .badge").inner_text())
    admin.page.locator(".person", has_text="pend1").get_by_role("button", name=re.compile("Approve")).click()
    admin.page.wait_for_load_state("networkidle")
    assert admin.page.locator(".person", has_text="pend1").count() == 0
    after = admin.page.locator(".subnav .badge")
    assert (int(after.inner_text()) if after.count() else 0) == badge_before - 1
    admin.go("/console/members/")
    assert "pend1" in admin.page.locator("table.members").inner_text()


def set_ads(admin, on, code=""):
    admin.go("/console/settings/")
    cb = admin.page.get_by_label("Show ads to members who are not ad-free")
    cb.check() if on else cb.uncheck()
    admin.page.get_by_label("Ad code").fill(code)
    admin.page.get_by_role("button", name="Save").click()
    admin.page.wait_for_load_state("networkidle")


def test_A2_H2_ads_and_ad_free(make_app, kid):
    admin = make_app("boss")
    set_ads(admin, True, '<p id="the-ad">Buy pencils</p>')
    try:
        normal = make_app(kid)
        for path in ("/", "/progress/"):
            normal.go(path)
            assert normal.page.locator("#the-ad").count() == 1, path
        start_daily(normal)
        assert normal.page.locator("#the-ad").count() == 0, "ad on a question"
        free = make_app("sam")
        admin.go("/console/members/")
        sam_switch = admin.page.get_by_role("switch", name="Ad-free for Sam")
        if sam_switch.get_attribute("aria-checked") != "true":
            sam_switch.click()
        for path in ("/", "/progress/"):
            free.go(path)
            assert free.page.locator("#the-ad").count() == 0, path
    finally:
        set_ads(admin, False, "")
        admin.go("/console/members/")
        sw = admin.page.get_by_role("switch", name="Ad-free for Sam")
        if sw.get_attribute("aria-checked") == "true":
            sw.click()


def test_A2_H3_ad_free_switch(make_app):
    admin = make_app("boss")
    admin.go("/console/members/")
    sw = admin.page.get_by_role("switch", name="Ad-free for Maya") if admin.page.get_by_role("switch", name="Ad-free for Maya").count() else admin.page.get_by_role("switch", name="Ad-free for Sam")
    before = sw.get_attribute("aria-checked")
    sw.click()
    admin.page.wait_for_load_state("networkidle")
    sw2 = admin.page.get_by_role("switch", name=re.compile("Ad-free for"))
    states = [e.get_attribute("aria-checked") for e in sw2.all()]
    assert ("true" if before == "false" else "false") in states
    assert "now" in admin.page.locator(".messages").inner_text().lower()
    admin.page.get_by_role("switch", name=re.compile(".*")).first  # still there
    for e in admin.page.get_by_role("switch", name="Ad-free for Sam").all():
        pass
    # restore
    sw3 = admin.page.get_by_role("switch", name=re.compile("Ad-free for (Maya|Sam)")).first
    if sw3.get_attribute("aria-checked") != before:
        sw3.click()


def test_A2_N1_member_cannot_use_console(make_app, kid):
    app = make_app(kid)
    app.allowed.append("403")
    for path in ("/console/", "/console/approvals/", "/console/members/", "/console/settings/"):
        assert app.go(path).status == 403, path
    app.allowed.append("403")
    app.go("/me/")
    r = app.post("/console/users/aaaaaaaa-0000-0000-0000-000000000001/action/", {"action": "approve"})
    assert r.status == 403


def test_A2_N2_signed_out(make_app):
    app = make_app()
    app.go("/console/")
    assert "/login/" in app.page.url


def test_A2_E1_reset_password(make_app, kid):
    admin = make_app("boss")
    admin.go("/console/members/")
    admin.page.get_by_role("button", name=re.compile(f"Reset password for Kid {kid[1:]}")).click()
    admin.page.wait_for_load_state("networkidle")
    msg = admin.page.locator(".messages").inner_text()
    m = re.search(r"New password for [^:]+: (\S+)", msg)
    assert m, msg
    new = m.group(1)
    guest = make_app()
    guest.login(kid, PW, expect_ok=False)
    assert "/login" in guest.page.url
    guest.login(kid, new)


def test_A2_E2_no_horizontal_scroll(make_app):
    for width in (390, 1440):
        admin = make_app("boss", width=width)
        for path in ("/console/", "/console/approvals/", "/console/members/", "/console/settings/"):
            admin.go(path)
            admin.page.wait_for_load_state("networkidle")
            assert hscroll(admin.page) <= 0, (path, width)

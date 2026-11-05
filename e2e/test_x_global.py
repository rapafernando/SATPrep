import re

import pytest
from conftest import BASE
from helpers import axe_violations, hscroll, start_daily, answer

PUBLIC = ["/login/", "/signup/", "/privacy/"]
MEMBER = ["/", "/practice/", "/progress/", "/me/", "/plan/", "/install/", "/password/", "/delete-account/", "/skills/linear-equations/"]
ADMIN = ["/console/", "/console/approvals/", "/console/members/", "/console/settings/"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_X_1_axe_every_screen(make_app, scheme):
    problems = []
    anon = make_app(scheme=scheme)
    for p in PUBLIC:
        anon.go(p)
        anon.page.wait_for_load_state("networkidle")
        problems += [(p, scheme, v) for v in axe_violations(anon.page)]
    member = make_app("sam", scheme=scheme)
    for p in MEMBER:
        member.go(p)
        member.page.wait_for_load_state("networkidle")
        problems += [(p, scheme, v) for v in axe_violations(member.page)]
    admin = make_app("boss", scheme=scheme)
    for p in ADMIN:
        admin.go(p)
        admin.page.wait_for_load_state("networkidle")
        problems += [(p, scheme, v) for v in axe_violations(admin.page)]
    assert not problems, "\n".join(f"{p} [{s}] {v['id']}: {v['help']} {v['nodes'][:1]}" for p, s, v in problems)


def test_X_1b_axe_question_review_done(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    probs = list(axe_violations(app.page))
    answer(app, db, right=False)
    probs += axe_violations(app.page)
    assert not probs, probs


def test_X_2_no_horizontal_scroll(make_app):
    anon = make_app()
    member = make_app("sam")
    bad = []
    for app, paths in ((anon, PUBLIC), (member, MEMBER)):
        for p in paths:
            app.go(p)
            app.page.wait_for_load_state("networkidle")
            if hscroll(app.page) > 0:
                bad.append(p)
    assert not bad, bad


def test_X_3_error_pages_are_friendly(make_app, kid):
    app = make_app(kid)
    app.allowed.append("Failed to load resource")
    r = app.go("/this-page-does-not-exist/")
    assert r.status == 404
    text = app.page.locator("body").inner_text()
    assert app.page.locator("link[rel=stylesheet]").count() >= 1, "404 page is unstyled"
    assert app.page.locator("a[href='/']").count() >= 1, "404 page has no way back"
    r = app.go("/console/")
    assert r.status == 403
    assert app.page.locator("a[href='/']").count() >= 1, "403 page has no way back"
    assert "Forbidden" not in app.page.locator("body").inner_text()[:12] or app.page.locator("link[rel=stylesheet]").count() >= 1


def test_X_5_focus_ring_visible(make_app, kid):
    app = make_app(kid)
    app.go("/")
    stops = 0
    for _ in range(14):
        app.page.keyboard.press("Tab")
        info = app.page.evaluate("""(() => {const a = document.activeElement; if (a === document.body) return null;
            const s = getComputedStyle(a); return {tag: a.tagName, w: parseFloat(s.outlineWidth), style: s.outlineStyle, shadow: s.boxShadow}})()""")
        if info:
            stops += 1
            assert (info["style"] != "none" and info["w"] >= 2) or "rgb" in info["shadow"], info
    assert stops >= 8

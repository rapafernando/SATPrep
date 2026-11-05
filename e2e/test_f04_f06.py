import re

from conftest import BASE
from helpers import answer, session_id, start_daily


def test_F04_H1_progress_with_history(make_app):
    app = make_app("sam")
    app.go("/progress/")
    text = app.page.locator("main").inner_text().lower()
    assert "predicted score" in text and "last 14 days" in text and "skills" in text
    labels = [l.get_attribute("aria-label") or "" for l in app.page.locator("svg.chart").all()]
    assert len(labels) == 2 and all(re.search(r"\d", l) for l in labels), labels
    assert "NaN" not in text and "None" not in text


def test_F04_E1_no_attempts_yet(make_app, kid):
    app = make_app(kid)
    app.go("/progress/")
    text = app.page.locator("main").inner_text()
    assert "predicted score" in text.lower()
    for bad in ("NaN", "None", "Infinity", "undefined", "Traceback"):
        assert bad not in text, bad
    assert app.page.locator("svg.chart").count() >= 1 or "Finish a session" in text


def test_F06_H1_parent_sees_child(make_app):
    app = make_app("dana")
    app.go("/me/")
    app.page.get_by_role("link", name=re.compile("Family")).click()
    app.page.wait_for_url("**/family/")
    text = app.page.locator("main").inner_text()
    low = text.lower()
    assert "sam" in low and "predicted score" in low and "target" in low and "day streak" in low


def test_F06_N1_student_cannot_open_family(make_app, kid):
    app = make_app(kid)
    app.allowed.append("404")
    assert app.go("/family/").status == 404
    app.go("/me/")
    assert app.page.get_by_role("link", name=re.compile("^Family")).count() == 0


def test_F06_N2_parent_without_link(make_app):
    app = make_app("lonely")
    app.go("/family/")
    assert "No children are linked" in app.page.locator("main").inner_text()


def test_F06_N3_parent_cannot_open_child_session(make_app, kid):
    child = make_app(kid)
    start_daily(child)
    sid = session_id(child)
    parent = make_app("dana")
    parent.allowed.append("404")
    assert parent.go(f"/practice/{sid}/").status == 404

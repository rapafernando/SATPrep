import re

import pytest
from conftest import BASE
from helpers import answer, current_question, hscroll, session_id, start_daily


def open_question(app, db, want_type=None, tries=25):
    """Start sessions until the current question has the wanted answer type (numeric or choice)."""
    start_daily(app)
    for _ in range(tries):
        q = current_question(app, db)
        if want_type is None or q["type"] == want_type:
            return q
        answer(app, db)
        app.page.get_by_role("button", name=re.compile("Next question|Finish")).click()
        app.page.wait_for_load_state("domcontentloaded")
    pytest.skip(f"no {want_type} question in the first {tries}")


def test_F03_H1_keyboard_only(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    page = app.page
    q = current_question(app, db)
    assert q["type"] in ("choice", "numeric")
    if q["type"] == "choice":
        page.locator("input[name=answer]").first.focus()
        page.keyboard.press("Space")
    else:
        page.locator("#answer").focus()
        page.keyboard.type("1")
    assert page.locator("#check-btn").is_enabled()
    page.keyboard.press("Enter")
    page.wait_for_url("**/review/")
    for _ in range(12):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.textContent.trim()") == "Next question":
            break
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/practice/[0-9a-f-]{36}/$"))
    assert "2/20" in page.locator(".focusbar").inner_text()


def test_F03_H2_right_and_wrong(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    answer(app, db, right=True)
    v = app.page.locator(".verdict")
    assert "right" in v.get_attribute("class") and "Correct!" in v.inner_text()
    assert v.locator("svg").count() == 1
    app.page.get_by_role("button", name="Next question").click()
    app.page.wait_for_load_state("domcontentloaded")
    answer(app, db, right=False)
    v = app.page.locator(".verdict")
    assert "wrong" in v.get_attribute("class") and "Not quite" in v.inner_text() and "The answer is" in v.inner_text()


def test_F03_E1_check_disabled_until_answered(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    assert app.page.locator("#check-btn").is_disabled()
    q = current_question(app, db)
    if q["type"] == "choice":
        app.page.locator("input[name=answer]").nth(1).check(force=True)
    else:
        app.page.locator("#answer").fill("2")
    assert app.page.locator("#check-btn").is_enabled()
    if q["type"] == "numeric":
        app.page.locator("#answer").fill("   ")
        assert app.page.locator("#check-btn").is_disabled()


def test_F03_E2_skip(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    app.page.get_by_role("button", name="Skip").click()
    app.page.wait_for_load_state("networkidle")
    row = db.q("select a.is_correct, a.answer from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid)
    assert row == [(0, "")]
    assert "Skipped" in app.page.locator(".verdict").inner_text() or "/review/" not in app.page.url


def test_F03_E3_numeric_equivalents(make_app, kid, db):
    app = make_app(kid)
    q = open_question(app, db, "numeric")
    answers = db.one("select correct_answer from learn_question where replace(id,'-','')=?", q["id"].replace("-", "")).split("|")
    app.page.locator("#answer").fill(answers[-1] if len(answers) > 1 else answers[0])
    app.page.get_by_role("button", name="Check answer").click()
    app.page.wait_for_url("**/review/")
    assert "Correct!" in app.page.locator(".verdict").inner_text()
    app.page.get_by_role("button", name="Next question").click()
    app.page.wait_for_load_state("domcontentloaded")
    # words, with thousands commas, with spaces: wrong but never a server error
    for typed in ("seven", "1,000", "  ", "3/0", "1e999", "٣"):
        q = current_question(app, db)
        if q["type"] != "numeric":
            break
        app.page.locator("#answer").fill(typed)
        if app.page.locator("#check-btn").is_enabled():
            app.page.get_by_role("button", name="Check answer").click()
            app.page.wait_for_url("**/review/")
            app.page.get_by_role("button", name=re.compile("Next question|Finish")).click()
            app.page.wait_for_load_state("domcontentloaded")


def test_F03_E4_huge_and_emoji_answers(make_app, kid, db):
    app = make_app(kid)
    q = open_question(app, db, "numeric")
    app.page.locator("#answer").fill("9" * 5000)
    app.page.get_by_role("button", name="Check answer").click()
    app.page.wait_for_load_state("networkidle")
    assert app.page.locator("body").inner_text()  # a page, not an error
    stored = db.one("select length(a.answer) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid)
    assert stored is None or stored <= 100
    if "/review/" in app.page.url:
        app.page.get_by_role("button", name=re.compile("Next question|Finish")).click()
        app.page.wait_for_load_state("domcontentloaded")
    for typed in ("🎓😀", "café", "<script>alert(1)</script>"):
        if app.page.locator("#answer").count():
            app.page.locator("#answer").fill(typed)
            app.page.get_by_role("button", name="Check answer").click()
            app.page.wait_for_load_state("networkidle")
            assert "<script>alert(1)</script>" not in app.page.content()
            if "/review/" in app.page.url:
                app.page.get_by_role("button", name=re.compile("Next question|Finish")).click()
                app.page.wait_for_load_state("domcontentloaded")


def test_F03_E5_double_click_check(make_app, kid, db):
    app = make_app(kid)
    q = open_question(app, db)
    if q["type"] == "choice":
        app.page.locator("input[name=answer]").first.check(force=True)
    else:
        app.page.locator("#answer").fill("3")
    app.page.get_by_role("button", name="Check answer").dblclick()
    app.page.wait_for_load_state("networkidle")
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 1


def test_F03_E6_refresh_on_review(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    answer(app, db, right=False)
    before = app.page.locator(".verdict").inner_text()
    app.page.reload()
    assert app.page.locator(".verdict").inner_text() == before
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 1


def test_F03_E7_calculator(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    app.page.get_by_role("button", name="Calculator").click()
    disp = app.page.get_by_label(re.compile("display|calculator", re.I)).first
    box = app.page.locator("#calc-panel input").first
    box.fill("12*3+4")
    box.press("Enter")
    assert "40" in (box.input_value() or app.page.locator("#calc-panel").inner_text())
    box.fill("1/0")
    box.press("Enter")
    assert "Infinity" not in app.page.locator("#calc-panel").inner_text() + box.input_value()
    box.fill("alert(document.cookie)")
    box.press("Enter")
    app.page.wait_for_timeout(200)
    assert not app.errors


def test_F03_E8_scratchpad(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    app.page.get_by_role("button", name="Scratchpad").click()
    c = app.page.locator("#pad")
    assert c.is_visible()
    b = c.bounding_box()
    app.page.mouse.move(b["x"] + 20, b["y"] + 20)
    app.page.mouse.down()
    app.page.mouse.move(b["x"] + 120, b["y"] + 80, steps=8)
    app.page.mouse.up()
    app.page.get_by_role("button", name="Undo").click()
    app.page.get_by_role("button", name="Clear").click()


def test_F03_E9_math_renders(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    for _ in range(20):
        stem = app.page.locator(".stem").inner_text()
        app.page.wait_for_load_state("networkidle")
        if app.page.locator(".katex").count():
            assert "$" not in app.page.locator(".stem").inner_text().replace("\\$", "")
            return
        answer(app, db)
        app.page.get_by_role("button", name=re.compile("Next question|Finish")).click()
        app.page.wait_for_load_state("domcontentloaded")
    pytest.fail("no question with math in the first 20")


def test_F03_E10_timer_advances(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    t0 = app.page.locator("#timer").inner_text()
    app.page.wait_for_timeout(2300)
    assert app.page.locator("#timer").inner_text() != t0


def test_F03_E11_phone_width(make_app, kid, db):
    app = make_app(kid, width=390)
    start_daily(app)
    assert hscroll(app.page) <= 0
    assert app.page.locator("#check-btn").is_visible()
    answer(app, db)
    assert hscroll(app.page) <= 0
    assert app.page.get_by_role("button", name="Next question").is_visible()

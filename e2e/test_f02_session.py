import re

from conftest import BASE
from helpers import answer, current_question, hscroll, session_id, start_daily


def test_F02_H1_full_daily_session(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    for i in range(20):
        answer(app, db, right=(i % 4 != 0))
        label = "Finish" if i == 19 else "Next question"
        app.page.get_by_role("button", name=label).click()
        app.page.wait_for_load_state("domcontentloaded")
    app.page.wait_for_url("**/done/")
    body = app.page.locator("main").inner_text()
    assert "Session complete" in body and "15 / 20" in body
    app.page.get_by_role("link", name="Back to Today").click()
    assert "20" in app.page.locator("main").inner_text()
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 20


def test_F02_H2_skill_practice(make_app, kid, db):
    app = make_app(kid)
    app.go("/practice/")
    app.page.get_by_role("link", name=re.compile("Linear equations")).first.click()
    app.page.get_by_role("button", name="Practice this skill").click()
    app.page.wait_for_url("**/practice/*/")
    sid = session_id(app).replace("-", "")
    qids = db.one("select question_ids from learn_practicesession where replace(id,'-','')=?", sid)
    import json
    for q in json.loads(qids):
        slug = db.one("select s.slug from learn_question q join learn_skill s on s.id=q.skill_id where replace(q.id,'-','')=?", q.replace("-", ""))
        assert slug == "linear-equations"


def test_F02_E1_leave_and_resume(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    for _ in range(3):
        answer(app, db)
        app.page.get_by_role("button", name="Next question").click()
        app.page.wait_for_load_state("domcontentloaded")
    app.page.get_by_role("link", name="Leave practice").click()
    app.page.wait_for_url(BASE + "/")
    app.page.get_by_role("button", name="Keep going").click()
    app.page.wait_for_url("**/practice/*/")
    assert "4/20" in app.page.locator(".focusbar").inner_text()


def test_F02_E2_back_button_cannot_answer_twice(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    sid = session_id(app)
    q = answer(app, db, right=False)
    app.page.go_back()
    app.page.wait_for_load_state("domcontentloaded")
    if app.page.locator("#check-btn").count():
        if q["type"] == "choice":
            app.page.locator(f"input[name=answer][value={q['correct'].upper()}]").check(force=True)
        else:
            app.page.locator("#answer").fill(q["correct"])
        app.page.get_by_role("button", name="Check answer").click()
        app.page.wait_for_load_state("networkidle")
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 1
    assert db.one("select is_correct from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 0


def test_F02_E3_two_tabs_one_attempt(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    url = app.page.url
    tab2 = app.ctx.new_page()
    tab2.on("console", lambda m: app.errors.append(m.text) if m.type == "error" else None)
    tab2.goto(url)
    q = current_question(app, db)
    for page in (app.page, tab2):
        if q["type"] == "choice":
            page.locator("input[name=answer]").first.check(force=True)
        else:
            page.locator("#answer").fill("1")
        page.get_by_role("button", name="Check answer").click()
        page.wait_for_load_state("networkidle")
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 1


def test_F02_E4_expired_session_mid_question(make_app, kid, db):
    app = make_app(kid)
    start_daily(app)
    url = app.page.url
    q = current_question(app, db)
    if q["type"] == "choice":
        app.page.locator("input[name=answer]").first.check(force=True)
    else:
        app.page.locator("#answer").fill("5")
    app.ctx.clear_cookies()
    app.page.get_by_role("button", name="Check answer").click()
    app.page.wait_for_load_state("networkidle")
    assert "/login/" in app.page.url
    app.page.get_by_label("Username").fill(kid)
    app.page.get_by_label("Password").fill("Correct-horse-battery-9")
    app.page.get_by_role("button", name="Sign in").click()
    app.page.wait_for_load_state("networkidle")
    assert url.split(BASE)[1] in app.page.url or app.page.url == BASE + "/"
    assert db.one("select count(*) from learn_attempt a join accounts_user u on u.id=a.user_id where u.username=?", kid) == 0


def test_F02_E5_other_members_session_is_404(make_app, kid, db):
    owner = make_app(kid)
    start_daily(owner)
    sid = session_id(owner)
    other = make_app("sam")
    other.allowed.append("404")
    for suffix in ("", "review/", "done/"):
        r = other.go(f"/practice/{sid}/{suffix}")
        assert r.status == 404, suffix
    other.go("/me/")
    r = other.post(f"/practice/{sid}/answer/", {"answer": "A"})
    assert r.status in (403, 404)


def test_F02_N1_no_goal_prompt(make_app, newbie):
    app = make_app(newbie)
    app.go("/practice/")
    text = app.page.locator("main").inner_text().lower()
    assert "goal" in text
    assert app.page.get_by_role("button", name="Start a mixed set").count() == 0

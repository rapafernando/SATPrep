import datetime

from conftest import BASE
from helpers import hscroll


def future(days):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def fill_goal(page, now="1000", goal="1300", date=None, minutes="30", school=""):
    page.get_by_label("Now").fill(now) if page.get_by_label("Now").count() else page.locator("#id_current_score").fill(now)
    page.locator("#id_target_score").fill(goal)
    page.locator("#id_test_date").fill(date or future(90))
    page.locator("#id_minutes_per_day").fill(minutes)
    page.locator("#id_target_school").fill(school)


def test_F01_H1_new_member_sets_goal_and_gets_plan(make_app, newbie, db):
    app = make_app(newbie)
    page = app.page
    page.goto(BASE + "/")
    assert page.url.endswith("/onboarding/")
    assert hscroll(page) <= 0
    fill_goal(page, date=future(60))
    page.get_by_role("button", name="Make my plan").click()
    page.wait_for_url("**/plan/")
    assert "Your plan is ready" in page.content()
    assert page.get_by_text("Days to test").is_visible() and "300" in page.locator(".stats").inner_text()
    page.get_by_role("link", name="Let's get started").click()
    page.wait_for_url(BASE + "/")
    assert "of 20" in page.locator("body").inner_text() or "of" in page.locator(".ring, body").first.inner_text()
    assert db.one("select count(*) from learn_goal g join accounts_user u on u.id=g.user_id where u.username=?", newbie) == 1


def test_F01_E1_empty_fields(make_app, newbie, db):
    app = make_app(newbie)
    page = app.page
    page.goto(BASE + "/onboarding/")
    for sel in ("#id_current_score", "#id_target_score", "#id_test_date", "#id_minutes_per_day"):
        page.locator(sel).fill("")
    page.get_by_role("button", name="Make my plan").click()
    page.wait_for_load_state("networkidle")
    assert page.url.endswith("/onboarding/")
    assert page.locator(".error").count() >= 3
    assert db.one("select count(*) from learn_goal g join accounts_user u on u.id=g.user_id where u.username=?", newbie) == 0


def test_F01_E2_target_below_current(make_app, newbie):
    app = make_app(newbie)
    app.go("/onboarding/")
    fill_goal(app.page, now="1400", goal="1300")
    app.page.get_by_role("button", name="Make my plan").click()
    assert "at or above where you are now" in app.page.content()


def test_F01_E3_bad_dates(make_app, newbie):
    app = make_app(newbie)
    app.go("/onboarding/")
    fill_goal(app.page, date=future(-1))
    app.page.get_by_role("button", name="Make my plan").click()
    assert "has not passed yet" in app.page.content()
    fill_goal(app.page, date=future(365 * 3))
    app.page.get_by_role("button", name="Make my plan").click()
    assert "within the next two years" in app.page.content()


def test_F01_E4_test_tomorrow(make_app, newbie):
    app = make_app(newbie)
    app.go("/onboarding/")
    fill_goal(app.page, goal="1600", date=future(1))
    app.page.get_by_role("button", name="Make my plan").click()
    app.page.wait_for_url("**/plan/")
    text = app.page.locator("main").inner_text()
    assert "ambitious" in text or "Consider" in text
    assert "NaN" not in text and "None" not in text and "Infinity" not in text


def test_F01_E5_minute_chips(make_app, newbie):
    app = make_app(newbie)
    app.go("/onboarding/")
    app.page.get_by_role("button", name="45", exact=True).click()
    assert app.page.locator("#id_minutes_per_day").input_value() == "45"


def test_F01_E6_double_click_submit(make_app, newbie, db):
    app = make_app(newbie)
    app.go("/onboarding/")
    fill_goal(app.page)
    app.page.get_by_role("button", name="Make my plan").dblclick()
    app.page.wait_for_load_state("networkidle")
    assert db.one("select count(*) from learn_goal g join accounts_user u on u.id=g.user_id where u.username=?", newbie) == 1


def test_F01_E7_change_goal_later(make_app, kid, db):
    app = make_app(kid)
    app.go("/me/")
    app.page.get_by_role("link", name="Change my goal").click()
    app.page.locator("#id_target_score").fill("1450")
    app.page.get_by_role("button", name="Make my plan").click()
    app.page.wait_for_url("**/plan/")
    assert "1450" in app.page.content()
    assert db.one("select count(*) from learn_goal g join accounts_user u on u.id=g.user_id where u.username=?", kid) == 1


def test_F01_E8_emoji_and_accents(make_app, kid):
    app = make_app(kid)
    app.go("/onboarding/")
    app.page.locator("#id_target_school").fill("Universidad de Córdoba 🎓")
    app.page.get_by_role("button", name="Make my plan").click()
    app.page.wait_for_url("**/plan/")
    assert "Universidad de Córdoba 🎓" in app.page.content()


def test_F01_N1_signed_out_redirects_and_returns(make_app, newbie):
    app = make_app()
    app.go("/onboarding/")
    assert "/login/" in app.page.url and "next=" in app.page.url
    app.page.get_by_label("Username").fill(newbie)
    app.page.get_by_label("Password").fill("Correct-horse-battery-9")
    app.page.get_by_role("button", name="Sign in").click()
    app.page.wait_for_load_state("networkidle")
    assert app.page.url.endswith("/onboarding/")
    app.ctx.clear_cookies()
    app.go("/plan/")
    assert "/login/" in app.page.url

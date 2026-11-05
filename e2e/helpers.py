import re

AXE = (__import__("pathlib").Path(__file__).parent / "vendor" / "axe.min.js").read_text()


def case_ids(doc):
    return re.findall(r"\b([A-Z]\d?-?[HEN]?\d+|X-\d)\b", doc or "")


def axe_violations(page, serious_only=True):
    page.evaluate(AXE) if not page.evaluate("typeof axe !== 'undefined'") else None
    result = page.evaluate("axe.run(document, {resultTypes: ['violations']}).then(r => r.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.slice(0,3).map(n => n.html.slice(0,120)), help: v.help})))")
    return [v for v in result if v["impact"] in ("serious", "critical")] if serious_only else result


def hscroll(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def start_daily(app):
    app.go("/")
    app.page.locator("form[action$='/practice/daily/'] button").click()
    app.page.wait_for_url("**/practice/*/")


def session_id(app):
    m = re.search(r"/practice/([0-9a-f-]{36})/", app.page.url)
    return m.group(1) if m else None


def current_question(app, db):
    """The Question row (id, type, correct answer) the page is showing, read from the database."""
    sid = session_id(app).replace("-", "")
    qids, pos = db.q("select question_ids, position from learn_practicesession where replace(id,'-','')=?", sid)[0]
    import json
    qid = json.loads(qids)[pos]
    row = db.q("select answer_type, correct_answer, choices from learn_question where replace(id,'-','')=?", qid.replace("-", ""))[0]
    return {"id": qid, "type": row[0], "correct": row[1].split("|")[0], "choices": row[2]}


def answer(app, db, right=True):
    q = current_question(app, db)
    page = app.page
    if q["type"] == "choice":
        letter = q["correct"].upper() if right else next(l for l in "ABCD" if l != q["correct"].upper())
        page.locator(f"input[name=answer][value={letter}]").check(force=True)
    else:
        page.locator("#answer").fill(q["correct"] if right else "999999")
    page.get_by_role("button", name="Check answer").click()
    page.wait_for_url("**/review/")
    return q

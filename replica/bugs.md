# Bugs: ScorePath

Found by `/replica-test` on 2026-11-05 (browser end-to-end tests, production-like server, plus a hand review of screenshots).
Every bug below was reproduced by a failing test first, then fixed, then the test kept.
Severity: S1 data loss or security hole or core flow blocked. S2 feature broken with no workaround. S3 broken with a workaround, or visibly wrong. S4 cosmetic.

Open S1: none. Open S2: none.

### BUG-001: "Keep going" starts a new set at question 1 instead of resuming

- Severity: S3
- Flow / case: F02 / F02-E1
- Screen: S11 Today
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Sign in, press Start today's set, answer 3 questions.
2. Press the X (Leave practice), then press Keep going on Today.

Expected: the same set continues at question 4.
Actual: a brand-new set opens at question 1/20. The first set stays unfinished forever, and answers already given do not count toward finishing it.
Evidence: `e2e/test_f02_session.py::test_F02_E1_leave_and_resume` (failed with '1/20').
Suspected cause: `start_daily` always created a session.
Status: fixed. `services.resumable_daily_session` reuses today's unfinished set. Tests: `learn.tests.ResumeTests` (4 cases) and the e2e case.

### BUG-002: a stale form (phone slept, cookies cleared) shows a bare 403 page

- Severity: S3
- Flow / case: F02 / F02-E4
- Screen: any form
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Open a question, choose an answer.
2. Clear site cookies (or let the phone sit until the session is gone), press Check answer.

Expected: sent to sign in with a plain message, or back to the page with "try again".
Actual: Django's raw "403 Forbidden, CSRF verification failed" page with no link back.
Evidence: `e2e/test_f02_session.py::test_F02_E4_expired_session_mid_question`.
Status: fixed. `CSRF_FAILURE_VIEW = core.views.csrf_failed` (signed out: to sign in with "Your session ended". Signed in: back to the page, never off-site). Tests: `core.tests.ErrorPageTests`.

### BUG-003: Practice tab says nothing about the mixed set when no goal is set

- Severity: S4
- Flow / case: F02 / F02-N1
- Screen: S22 Practice
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Sign in as a member who has no goal yet and open the Practice tab.

Expected: a hint that a goal unlocks the daily mixed set.
Actual: the Mixed set card was silently missing.
Evidence: `e2e/test_f02_session.py::test_F02_N1_no_goal_prompt`.
Status: fixed. A card explains it and links to Set my goal. Test: `ResumeTests.test_practice_tab_without_goal_explains_the_mixed_set`.

### BUG-004: the lockout page is bare text with no way back

- Severity: S3
- Flow / case: A1 / A1-E4
- Screen: S08 Sign in
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Enter a wrong password six times for one username.
2. Try the right password.

Expected: a page in the app's style that says why and what to do.
Actual: one unstyled line from django-axes (HTTP 429) with no link back to sign in.
Evidence: `e2e/test_a1_signup.py::test_A1_E4_lockout` ("lockout page is a dead end").
Status: fixed. `AXES_LOCKOUT_TEMPLATE = accounts/locked.html`. Test: `ErrorPageTests.test_lockout_page_is_friendly_and_in_the_app_style`.

### BUG-005: a long name with no spaces widens the admin pages on a phone

- Severity: S3
- Flow / case: A2 / A2-E2
- Screen: X3 Console approvals (also Members, Family, headings)
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Sign up with a 60 character name made of one unbroken word.
2. As admin, open Approvals at 390px.

Expected: the name wraps and the page stays one screen wide.
Actual: the page scrolls sideways, pushing the Approve button off screen.
Evidence: `e2e/test_a2_console.py::test_A2_E2_no_horizontal_scroll` (failed only after the sign-up tests created the long name).
Status: fixed with `overflow-wrap: anywhere` on names, stats and headings.

### BUG-006: 404, 403 and 500 pages are unstyled and have no way back

- Severity: S3
- Flow / case: X / X-3
- Screen: error pages
- Build: before replica-test  Browser / device: Chromium, 390px

Steps
1. Open /no-such-page/ or, as a member, /console/.

Expected: a readable page in the app's look with a button to go back.
Actual: Django's default plain text pages.
Evidence: `e2e/test_x_global.py::test_X_3_error_pages_are_friendly`.
Status: fixed. `templates/404.html`, `403.html`, `500.html` (the 500 page is standalone so it still renders if the app is broken). Tests: `ErrorPageTests`.

## To check (not reproduced, so not bugs)
- The calculator accepts only arithmetic; an attempt to enter code-like text showed no console error. Reviewed `static/js/calc-core.js`, a hand-written parser with no `eval`. Not tested against an external security review.
- Apple Pencil palm rejection is untested on a real iPad.
- Two sign-up attempts from one phone address behind carrier-grade NAT share the 5-per-hour limit. Fine for a family. Raise `SIGNUPS_PER_HOUR` if it bites.

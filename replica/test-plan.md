# Test plan: ScorePath

Date: 2026-11-05  Env: local, production-like (DEBUG off, collected static files, SQLite, fresh seed)
Run: `E2E_PYTHON=<python with Django> python -m pytest e2e` then `python e2e/report.py`

The original app was never touched. All tests run against this clone.

Summary: 66 e2e cases passed, 0 failed, 0 not run, 1 covered by Django unit tests.

| case | flow | type | steps | expected | auto | result |
| --- | --- | --- | --- | --- | --- | --- |
| F01-H1 | F01 goal and plan | happy | Sign in as a new member, land on goal, fill 1000 to 1300, a date, 30 minutes, submit, press Let's get started | Plan shows days left and 300 points, Today shows 0 of N | e2e | pass |
| F01-E1 | F01 goal and plan | edge: empty fields | Clear every field and submit | Errors shown, no goal saved, no 500 | e2e | pass |
| F01-E2 | F01 goal and plan | edge: target below current | Now 1400, goal 1300 | Clear error on the goal field | e2e | pass |
| F01-E3 | F01 goal and plan | edge: date in the past or 3 years out | Enter yesterday, then a date 3 years ahead | Both refused with a message | e2e | pass |
| F01-E4 | F01 goal and plan | edge: test tomorrow | Test date is tomorrow, target 1600 | Plan renders, a hard-pace note, no divide by zero | e2e | pass |
| F01-E5 | F01 goal and plan | edge: minute chips | Press 45 | Field becomes 45 | e2e | pass |
| F01-E6 | F01 goal and plan | edge: double click submit | Double click Make my plan | Exactly one goal exists | e2e | pass |
| F01-E7 | F01 goal and plan | edge: change goal later | Me, Change my goal, save new target | Goal updated, still one row | e2e | pass |
| F01-E8 | F01 goal and plan | edge: emoji and accents in school | School is 'Universidad de Córdoba 🎓' | Saved and shown intact | e2e | pass |
| F01-N1 | F01 goal and plan | negative: not signed in | Open /onboarding/ and /plan/ signed out | Sent to sign in, then back after signing in | e2e | pass |
| F02-H1 | F02 daily session | happy | Today, Start today's set, answer all 20 (Check, Next), Finish | Done page shows score, Today ring updates | e2e | pass |
| F02-H2 | F02 daily session | happy: skill practice | Practice tab, open a skill, Practice this skill | Every question belongs to that skill | e2e | pass |
| F02-E1 | F02 daily session | edge: leave mid-session | Answer 3, press X, open Today | Button says Keep going and resumes at question 4 | e2e | pass |
| F02-E2 | F02 daily session | edge: back button from review | Answer, press browser Back, try to answer again | No second attempt is recorded | e2e | pass |
| F02-E3 | F02 daily session | edge: two tabs same question | Open the question in two tabs, answer in both | One attempt only | e2e | pass |
| F02-E4 | F02 daily session | edge: expired session mid-question | Clear cookies, press Check | Sent to sign in, no 500, no lost data after sign-in | e2e | pass |
| F02-E5 | F02 daily session | edge: another member's session URL | Open someone else's session URL | 404 on every session page | e2e | pass |
| F02-N1 | F02 daily session | negative: no goal yet | Member without goal opens /practice/ | Prompt to set a goal, no crash | e2e | pass |
| F03-H1 | F03 answer a question | happy: multiple choice by keyboard only | Tab to a choice, Space, Enter, then Tab to Next, Enter | Review shown, flow completed without a mouse | e2e | pass |
| F03-H2 | F03 answer a question | happy: right and wrong states | Answer correctly, then wrongly | Correct! / Not quite with icon and words, the right answer shown | e2e | pass |
| F03-E1 | F03 answer a question | edge: Check disabled until answered | Open a question | Check answer disabled, enabled after choosing | e2e | pass |
| F03-E2 | F03 answer a question | edge: skip | Press Skip | Counted as a miss, next question, verdict says Skipped | e2e | pass |
| F03-E3 | F03 answer a question | edge: numeric forms | Type 3/4, 0.75, 1,000, -2, and words | Equivalent forms graded right, words wrong, none 500 | e2e | pass |
| F03-E4 | F03 answer a question | edge: 5000 characters and emoji | Paste 5000 characters, then emoji and accents, into the numeric answer | Handled as a wrong answer, no 500 | e2e | pass |
| F03-E5 | F03 answer a question | edge: double click Check | Double click Check answer | One attempt | e2e | pass |
| F03-E6 | F03 answer a question | edge: refresh on review | Reload the review page | Same verdict, no new attempt | e2e | pass |
| F03-E7 | F03 answer a question | edge: calculator | 12*3+4, then 1/0, then a code-like string | 40, a plain error for 1/0, code never runs | e2e | pass |
| F03-E8 | F03 answer a question | edge: scratchpad | Open it, draw with the mouse, Undo, Clear | No console error, canvas present | e2e | pass |
| F03-E9 | F03 answer a question | edge: math renders | Open a question with $...$ | KaTeX output present, no raw dollar signs left | e2e | pass |
| F03-E10 | F03 answer a question | edge: timer | Wait 2 seconds | Timer text advances | e2e | pass |
| F03-E11 | F03 answer a question | edge: 390px width | Question and review at 390px | No horizontal scroll, Check bar visible | e2e | pass |
| F04-H1 | F04 progress | happy | Open Progress as a member with history | Predicted score, two charts with numbers in aria-labels, skills list | e2e | pass |
| F04-E1 | F04 progress | edge: no attempts yet | New member with a goal opens Progress | Empty states, no NaN or None text | e2e | pass |
| F04-E2 | F04 progress | edge: dates and time zones | Streak across midnight and daylight saving | Streak and daily buckets use the local day | unit (learn.tests) | pass (unit) |
| F06-H1 | F06 parent follows child | happy | Parent signs in, opens Family | Linked child's score, target, streak and today count | e2e | pass |
| F06-N1 | F06 parent follows child | negative: student opens Family | Student opens /family/ | 404 | e2e | pass |
| F06-N2 | F06 parent follows child | negative: parent without link | Parent with no child opens Family | Friendly empty message | e2e | pass |
| F06-N3 | F06 parent follows child | negative: parent opens child's session URL | Parent opens a child's session URL | 404 | e2e | pass |
| A1-H1 | A1 sign-up and approval | happy | Sign up, see thank-you, try to sign in (waiting notice), admin approves, sign in | Lands on goal screen | e2e | pass |
| A1-E1 | A1 sign-up and approval | edge: duplicate username, any case | Sign up as SAM | Taken message | e2e | pass |
| A1-E2 | A1 sign-up and approval | edge: weak or mismatched password | 12345678; then two different passwords | Clear errors, no account | e2e | pass |
| A1-E3 | A1 sign-up and approval | edge: emoji and long name | Name with emoji and accents; 80 character name | Emoji saved and shown; long name refused cleanly | e2e | pass |
| A1-E4 | A1 sign-up and approval | edge: lockout | Six wrong passwords for one username | Locked with a message; right password still refused during lockout | e2e | pass |
| A1-E5 | A1 sign-up and approval | edge: sign-up rate limit | Six sign-up attempts from one address | Sixth refused with a wait message | e2e | pass |
| A1-E6 | A1 sign-up and approval | edge: sign-ups closed | Admin turns sign-ups off | Closed page, no form | e2e | pass |
| A1-N1 | A1 sign-up and approval | negative: rejected member | Rejected member signs in | No access message | e2e | pass |
| A1-N2 | A1 sign-up and approval | negative: access removed while signed in | Admin removes access, member clicks any link | Signed out with a message | e2e | pass |
| A2-H1 | A2 admin console | happy: approvals | Admin opens Approvals, approves one | Badge count drops, member listed under Members | e2e | pass |
| A2-H2 | A2 admin console | happy: ads and ad-free | Turn ads on with sample code; compare a normal and an ad-free member | Normal member sees the slot on Today, Progress, Done and never on a question; ad-free sees none | e2e | pass |
| A2-H3 | A2 admin console | happy: ad-free switch | Flip the switch for one member | State changes at once, aria-checked correct | e2e | pass |
| A2-N1 | A2 admin console | negative: member opens console | Member opens /console/ and posts an action | 403 | e2e | pass |
| A2-N2 | A2 admin console | negative: signed out | Open /console/ signed out | Sent to sign in | e2e | pass |
| A2-E1 | A2 admin console | edge: reset password | Reset a member's password and sign in with the new one | Works once, old password dead | e2e | pass |
| A2-E2 | A2 admin console | edge: 390px and 1440px | Open every console page at both widths | No horizontal page scroll | e2e | pass |
| A3-H1 | A3 account self-service | happy: change password | Me, Change password | Old password refused afterwards, new works | e2e | pass |
| A3-H2 | A3 account self-service | happy: sign out everywhere | Sign in on two browsers, sign out everywhere on one | Both signed out; another member untouched | e2e | pass |
| A3-H3 | A3 account self-service | happy: delete account | Me, Delete my account, enter password | Cannot sign in, other members unaffected | e2e | pass |
| A3-E1 | A3 account self-service | edge: wrong password on delete | Wrong password | Stays, nothing deleted | e2e | pass |
| A4-H1 | A4 install and offline | happy: manifest | Fetch /manifest.webmanifest | Name, standalone, start_url, 192 and 512 icons that load | e2e | pass |
| A4-H2 | A4 install and offline | happy: service worker | Load Today | Worker active with scope / | e2e | pass |
| A4-H3 | A4 install and offline | happy: iPhone hint | iPhone user agent, open Today | Banner with the Share hint; Not now hides it and it stays hidden after reload | e2e | pass |
| A4-E1 | A4 install and offline | edge: offline | Load once, go offline, open another page | Offline page, not a browser error | e2e | pass |
| A4-E2 | A4 install and offline | edge: private pages not cached | Sign out, go offline, open /progress/ | No cached private content | e2e | pass |
| X-1 | X cross-cutting | accessibility | axe scan of every screen at 390px in light and dark | No serious or critical violations | e2e | pass |
| X-2 | X cross-cutting | layout | Every screen at 390px | No horizontal scroll | e2e | pass |
| X-3 | X cross-cutting | errors pages | Open a missing URL and a forbidden one | Readable page with a way back | e2e | pass |
| X-4 | X cross-cutting | console and server errors | Every spec | No console error, no 5xx | e2e (every test) | pass |
| X-5 | X cross-cutting | keyboard focus | Tab through Today | Visible 3px focus ring on each stop | e2e | pass |

## Flows from the recon map that are not built, so not tested
F05 the original's daily timed game, F07 AI coach, F08 multiplayer, F09 subscribe or cancel (skipped on purpose for a private app).

## Needs a hand check (cannot be automated here)
- Apple Pencil drawing on a real iPad (palm rejection).
- "Add to Home Screen" on a real iPhone and Android phone, including the Android Install button.
- Screen reader pass (VoiceOver, TalkBack). The axe scan finds missing labels and contrast, not reading order or wording.
- Docker Compose start on the rapamedia server and https through Caddy.

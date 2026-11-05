# Build log: ScorePath

Screens are listed by the recon ID of the original screen they replace. `X` screens exist only in the clone.
Each was checked at 390 px and 1440 px (light), at 390 px dark, keyboard only, with zero console errors.
Screenshots: `replica/clone-screens/<id>-<name>[-wide|-dark].png`.

| ID | Screen | Date | Status | Missing / harder than expected |
| --- | --- | --- | --- | --- |
| S06 | Goal (onboarding) | 2026-11-05 | done | One screen, not a multi-step flow. Starter values prefilled. No projected-curve hook before sign-up |
| S08 | Sign in (+ error, waiting-for-approval states) | 2026-11-05 | done | Found raw `%(username)s` in the error text, fixed with a test |
| S08b | Sign up (+ closed, thank-you) | 2026-11-05 | done | Honeypot and rate limit stay hidden by design |
| S11 | Today | 2026-11-05 | done | Ring shows the real count even above the goal (e.g. 101 of 20 after heavy testing) |
| S12 | Plan summary | 2026-11-05 | done | No study calendar (S13) |
| S14 | Skill detail | 2026-11-05 | partial | Only 6 of the skills have a written lesson |
| S15 | Question (choice and numeric) | 2026-11-05 | done | Single bar, not segments. No flag/bookmark |
| S16 | Review (right and wrong) | 2026-11-05 | done | Wrong state now says what you chose and the answer, with icon and words |
| S17 | Progress | 2026-11-05 | done | Chart text was too small at phone width; enlarged. No share, no school list |
| S18 | Me | 2026-11-05 | done | Replaces the profile screen; avatar not built |
| S19 | Session done | 2026-11-05 | done | Ad slot shown here only when allowed |
| S22 | Practice tab | 2026-11-05 | done | Locked nodes not built on purpose |
| S23 | Calculator | 2026-11-05 | done | Safe parser, no eval |
| S24 | Scratchpad | 2026-11-05 | partial | Palm rejection written but untested on a real Apple Pencil |
| S26 | Family (parent view) | 2026-11-05 | done | Admin links children; no invite flow |
| X1 | Install help | 2026-11-05 | done | Android Install now button only appears where the browser allows it |
| X2 | Console overview | 2026-11-05 | done | |
| X3 | Console approvals | 2026-11-05 | done | |
| X4 | Console members (ad-free switch) | 2026-11-05 | done | Table reflows to stacked rows under 640 px (admin on a phone) |
| X4b | Console ads and sign-ups | 2026-11-05 | done | |
| X5 | Offline page | 2026-11-05 | done | |

## Bigger than it looked
- Question bank: 24 original questions in 6 skills. A real prep app needs hundreds. This is the dominant cost and is content writing, not code.
- Scratchpad on a real iPad with Apple Pencil still needs a hands-on test.
- Docker Compose files were written but not run on the rapamedia server yet.

## Checks
- 76 Django tests pass (SQLite). Includes the WCAG contrast gate and tokens-up-to-date check.
- Keyboard flow tested: sign in, start set, choose answer with Space, Check with Enter, Next.
- No raw hex in components: colours come from `var(--color-*)` in `static/css/tokens.css`.

# ScorePath components

Tokens: `replica/design/tokens.json` (roles and values), built into `static/css/tokens.css` by
`python3 tools/build_tokens.py`. Components live in `static/css/app.css` and use only token variables
(`var(--color-accent)`, `var(--radius-lg)`, `var(--text-md)`), never raw hex. Live specimens: `/design/`
(staff only). A test fails if `tokens.css` is stale or any colour pair drops below WCAG AA in light or dark.

Global rules
- Every tappable thing is at least 44 px tall (`--size-touch`); main actions 52 px (`--size-action`).
- Focus ring: 3 px `accent`, 2 px offset, on every interactive element, never removed.
- Right and wrong always carry words and an icon or mark, never colour alone.
- `goal` gold is a fill only (behind `on-goal` ink or with an ink ring). It fails 3:1 as a line or text on light grounds.
- Dark mode follows the phone (`prefers-color-scheme`); roles are identical, values differ.
- Reduced motion: transitions use `--motion-*`; none are required to understand state.

```
Button  (.btn)
  variants  primary (accent), secondary (.ghost: surface, 2px accent border), danger (.danger), small (.small, 44px)
  sizes     default 52px, small 44px, block (.block, full width)
  states    default, hover (none; touch first), active (drops 2px, press edge shrinks), focus-visible, disabled
            (border fill, muted text, no edge, not-allowed), loading (not used: forms post and reload)
  tokens    bg accent, text on-accent, radius control (14), font md 17/700, edge shadow-press (accent-pressed)
  a11y      real <button> or <a>; disabled uses the disabled attribute or aria-disabled; label never changes to an icon
  used on   every screen

Field  (.field, input, select, textarea)
  states    default (2px border-input), focus (accent ring), error (.has-error: danger border + .error text + aria-invalid),
            disabled, help text (.help)
  tokens    bg surface, border border-input (3.5:1 on surface), radius md (12), text md 17
  a11y      visible <label for>, error text linked with aria-describedby, honeypot field is off-screen and tabindex -1
  used on   sign in, sign up, goal, console settings

Answer choice  (.choices .choice)
  states    unselected (border), selected (accent border + accent-soft fill + filled letter), focus-visible (ring on label),
            correct/incorrect are shown on the review card, not on the choices
  tokens    surface, radius lg (16), min height 60, letter badge radius 10 in display font
  a11y      native radio inside a <label>, grouped in a <fieldset> with a legend; selection is not colour-only (letter fills)
  used on   question

Card  (.card, .result.right/.wrong)
  tokens    surface, 1px border, radius xl (20), padding 18, no shadow
  states    result.right / result.wrong add a success / danger border; the heading says "Correct!" or "Not quite"
  a11y      sections get headings; the result heading is the first thing after navigation

Stat  (.stats .stat)
  tokens    surface, radius lg, number in display font (xl), label xs/700 in text-muted
  states    default only; empty values show a dash, never 0 for "no data"

Meter and segments  (.meter, .segments)
  tokens    track accent-soft, fill accent (done segments success)
  a11y      role="progressbar" with aria-valuenow/min/max and a text equivalent ("12 of 20 questions today")

Chip  (.chip, .good, .off)
  variants  neutral, good (success text and border), off (danger text and border)
  a11y      the chip always has words; colour only reinforces

Message  (.messages .msg, .success, .error)
  tokens    notice-soft / success-soft / danger-soft with the matching on-* text
  a11y      rendered in the page flow near the top; error messages say what to do next

Path node  (.path .node)
  states    new (empty ring), learning (accent ring and dot), strong (success fill); the chip beside it names the state
  tokens    ring border-input, 22 px, whole row is the link (44px+ tall)

Question tools  (.tools, #pad, .calc)
  states    closed, open; scratchpad ignores finger touches once a pen is seen (palm rejection)
  tokens    calculator keys surface with border-input, op keys accent text, equals key accent fill
  a11y      toggles are <button aria-expanded>; display input has aria-label; canvas is optional, not required to answer

Ad slot  (.ad-slot)
  tokens    surface, 1px dashed border, "Sponsored" label in text-muted
  rules     only on home, progress and session summary; never on a question; hidden when ads are off or member is ad-free

Install banner  (.install-banner)
  states    hidden (default), Android install prompt, iPhone hint, dismissed for two weeks
  tokens    surface, radius xl, safe-area aware bottom offset

Navigation  (.topbar .nav, .subnav)
  current    text links, 44px touch rows. Planned for /replica-build: bottom tab bar on phones (Today, Practice, Progress, Me)
             as drawn on the design canvas; top bar stays on wide screens.
```

Charts (`.chart`): the score line and bars use `accent`; the goal line uses `success` dashed with a text label.
Every chart has an `aria-label` that states the numbers, because the picture alone is not enough.

<!-- capsule-v2 -->
# captcha-coordinate-playbook — how are CAPTCHAs driven when they live in cross-origin iframes with no DOM hooks?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What is the coordinate-driven recipe per CAPTCHA family, and which stale-bounds/lazy-mount traps invalidate it?

## Three-family coordinate playbook
**Path/Symbol:** `skills/cdp/interaction-skills/captcha.md` whole doc — locate (:7–25), checkbox (:27–42), slider/puzzle (:44–69), text/image (:71–93), image-grid (:95–119), Traps (:121–129).
**Signature:** locate via parent-page `Runtime.evaluate`: `[...document.querySelectorAll('iframe')].find(i => /recaptcha|hcaptcha|challenges\.cloudflare\.com/.test(i.src))` → `getBoundingClientRect()` = page coords.
**Data Shape:** three families: checkbox (reCAPTCHA v2/hCaptcha/Turnstile), slider/puzzle drag (pointer-based), text/image (vision-read + insertText). reCAPTCHA checkbox sits ~28px from iframe left edge (`widget.x + 28`, NOT center); slider = 30 interpolated mouseMoved steps @12ms (~360ms human-ish cadence) + optional y-jitter; image grid re-locates via `/recaptcha/api2/bframe` src.

### Decisive source
```md
- **Challenge iframes are lazy-mounted.** The grid iframe doesn't exist until
  after the checkbox click. Re-query `document.querySelectorAll('iframe')`
  when it appears; cached bounds from the checkbox stage point at the wrong frame.
```

**Flow:** screenshot FIRST (Turnstile often auto-verifies; don't click a ticked box) → click checkbox → wait 2500ms → RE-SCREENSHOT (click can silently escalate to a 3×3 grid) → re-query iframe bounds for the challenge frame → vision-classify cells → click cells at 200ms cadence → loop on pagination until widget verified.
**Invariant:** Never `contentDocument` the widget (cross-origin throws); compositor input passes through OOPIFs so coordinates are always available (see oopif-target-routing). Coordinates die at every visual transition — re-screenshot after EVERY state change; spinners/fade-ins move the next target. `Input.insertText` needs focus first: click the input by coordinate before typing, even inside OOPIFs where evaluate-writes may be sandboxed but compositor input still works.
**Probe:** `grep -cF 'widget.x + 28' skills/cdp/interaction-skills/captcha.md` → 1; `grep -cF 'Re-screenshot after every state change' <same>` → 1; `grep -cF 'api2/bframe' <same>` → 1; `grep -cF 'lazy-mounted' <same>` → 1; `grep -cF 'const steps = 30' <same>` → 1; `grep -cF 'jitter' <same>` → 2.
**Retrieve:** search_code --project browser-harness-js --pattern "captcha" (Module node resolves lines 16/83/100).

## Verdict
Adopt the family dispatch + screenshot-before-and-after-every-state-change discipline as the portable playbook. Adapt pixel offsets (28px is current-reCAPTCHA-specific) and cadences to observed widgets. Omit nothing else — the traps ARE the capsule.

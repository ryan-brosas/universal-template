<!-- capsule-v2 -->
# iframe-coordinate-passthrough — when does input cross frame boundaries without attaching, and when must you attach to an OOPIF?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What is the decision ladder between contentDocument, coordinate clicks, and session.use(iframeTargetId)?

## Same-origin vs OOPIF routing ladder
**Path/Symbol:** `skills/cdp/interaction-skills/iframes.md` whole doc + `skills/cdp/interaction-skills/cross-origin-iframes.md` whole doc.
**Signature:** OOPIF DOM access: `Target.getTargets()` → find `type === 'iframe' && url.includes(...)` → `session.use(iframe.targetId)` → Runtime/DOM/Network route there → `session.use(parentTargetId)` back. `Target.*`/`Browser.*` ALWAYS hit the browser endpoint regardless of `use`.
**Data Shape:** same-origin: contentDocument walk (throws "Blocked a frame with origin…" = your switch signal); coordinates: compositor-level Input passes through ALL frame boundaries (lowest friction, undetectable); OOPIF DOM: attach via use(). Disambiguating same-origin iframes under one origin: filter by URL path, map parent `<iframe>` src order to targets, or getTargetInfo title.

### Decisive source
```md
- **An OOPIF is not always present until interaction.** Stripe's card iframe
  is lazy-mounted after you focus the outer input. Screenshot +
  coordinate-click the outer input first, then re-query `Target.getTargets`.
- **OOPIF targets disappear when the parent navigates.** A cached
  `iframe.targetId` from before a navigation is dead.
```

**Flow:** can I see it? → coordinate click (no attach) → need DOM read/write? → same-origin contentDocument / cross-origin session.use(iframe) → done → USE PARENT BACK. Same-origin frame can BECOME cross-origin mid-flow (OAuth redirect inside the frame) — re-check contentDocument truthiness; null right after insertion until `load`.
**Invariant:** The two silent killers are stale targetIds after navigation and forgetting to switch back — a subsequent Page.navigate then hits the INSIDE of the iframe. CSP/sandbox may no-op evaluate WRITES even while attached (reads usually fine). Iframe-internal getBoundingClientRect is iframe-local — add the iframe rect offset before Input.* (page coords).
**Probe:** `grep -cF 'iframe-local' skills/cdp/interaction-skills/iframes.md` → 1; `grep -cF 'become cross-origin after navigation' <same>` → 1; `grep -cF 'session.use(iframe.targetId)' skills/cdp/interaction-skills/cross-origin-iframes.md` → 4; `grep -cF 'lazy-mounted' <same>` → 1; `grep -cF 'is dead' <same>` → 1; `grep -cF 'always hit the browser endpoint' <same>` → 1; `grep -cF 'switch back' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "OOPIF" (both Module nodes resolve line-exact).

## Verdict
Adopt the three-rung ladder (coordinates → contentDocument → use()) with its re-query-after-interaction rule as portable doctrine. Adapt URL-path disambiguation per embedded vendor. Omit postMessage patterns if your surfaces never need parent→frame messaging.

<!-- capsule-v2 -->
# buddy teaser window — how does a feature announce itself exactly once during a dated promo window, then go permanently quiet?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you ship a time-boxed in-product teaser that shows on startup for non-hatched users, disappears forever afterward, yet leaves the command live — without persisting any "shown" flag?

## useBuddyNotification.tsx: date-window + companion-state gates over a keyed removable notification
**Path/Symbol:** `src/buddy/useBuddyNotification.tsx`:`isBuddyTeaserWindow` (`:12-16`), `isBuddyLive` (`:17-21`), `useBuddyNotification` (`:43-78`), `findBuddyTriggerPositions` (`:79-97`).
**Signature:** `isBuddyTeaserWindow(): boolean`; `isBuddyLive(): boolean`; `useBuddyNotification(): void` (React hook); `findBuddyTriggerPositions(text: string): Array<{ start: number; end: number }>`.
**Data Shape:** Notification payload `{ key: "buddy-teaser", jsx: RainbowText, priority: "immediate", timeoutMs: 15000 }`. Window constants: year === 2026 && month index === 3 (April) && day ≤ 7; liveness = year > 2026 || (2026 && month ≥ 3).

### Decisive source
```ts
// Local date, not UTC — 24h rolling wave across timezones. Sustained Twitter
// buzz instead of a single UTC-midnight spike, gentler on soul-gen load.
export function isBuddyTeaserWindow(): boolean {
  if ("external" === 'ant') return true          // internal-build always-on override
  const d = new Date()
  return d.getFullYear() === 2026 && d.getMonth() === 3 && d.getDate() <= 7
}
...
if (!feature("BUDDY")) return                    // gate 1: build flag
const config = getGlobalConfig()
if (config.companion || !isBuddyTeaserWindow()) return   // gate 2+3
addNotification({ key: "buddy-teaser", ..., priority: "immediate",
                  timeoutMs: 15000 })
return () => removeNotification("buddy-teaser")  // effect cleanup removes it
```

**Flow:** startup hook effect → feature("BUDDY") build gate → already-companioned OR outside April 1–7 2026 ⇒ silent → otherwise push an immediate-priority rainbow "/buddy" notification with a 15s timeout; the effect returns a cleanup that removes it by key on unmount → once hatched (companion exists) the same gates stay false FOREVER — no persistence needed since both conditions are derived from current world-state each launch.
**Invariant:** Idempotence comes from DERIVING eligibility from state (feature flag × config.companion × wall clock), never from storing a shown-flag — the teaser cannot double-fire within a session because mount/unmount owns add/remove by key, and cannot leak past the window because the date predicate hard-fails. LOCAL time (not UTC) is deliberate: a 24h rolling wave across timezones sustains buzz and flattens load spikes. `isBuddyLive` uses month ≥ 3 so April 1 onward stays permanent; `"external" === 'ant'` is a dead-at-runtime internal override compiled per distribution channel. `findBuddyTriggerPositions` scans free text with `/\buddy\b/g`-style regex (`/\/buddy\b/g`) gated on the same feature flag — trigger highlighting shares the single kill-switch.
**Probe:** Coverage caveat: no upstream test on this host (graph flags the file clean: no_recorded_issue). Deterministic probe: `search_graph --project locoagent --name-pattern "isBuddyTeaserWindow|useBuddyNotification"` resolves all anchors line-exact; grep pins the local-date comment at `src/buddy/useBuddyNotification.tsx:9-11`, the three-gate ladder at `:53-59`, and the cleanup-return at `:66`. Call graph: `trace_path --function-name locoagent.src.buddy.useBuddyNotification.useBuddyNotification --direction both` (callees_total 33 incl. notifications store + tail-agent watchFile).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "useBuddyNotification isBuddyTeaserWindow buddy teaser", limit: 10 });
```

## Verdict
Adopt state-derived idempotence for one-shot announcements (derive from feature×state×clock instead of persisting a shown-flag) and key-based notification removal in effect cleanup. Adapt window dates, config field (`config.companion`), and notification store API. Omit the internal-channel override and React-compiler runtime artifacts. Caveat: source-grounded probes only — no runnable test host here.

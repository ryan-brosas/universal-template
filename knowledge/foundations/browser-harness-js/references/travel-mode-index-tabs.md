<!-- capsule-v2 -->
# Index-Based Travel-Mode Tabs — aria-labels are localized, DOM order is not

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How do you select a Google Maps travel mode (driving/transit/walking/cycling/flights/best) reliably across locales and unavailable modes?

## Path / Symbol
`skills/gmaps/scripts/gmaps` :261-334 (tab wait + selection + duration re-render poll); mode index map :262; flights body-scope flag :263.

## Signature
```js
const modeIdx = { best:0, driving:1, transit:2, walking:3, cycling:4, flights:5 }[mode];
// Tabs = button[role=radio] elements CONTAINING an [aria-label] icon, in stable DOM order:
// [Best, Driving, Transit, Walking, Cycling, Flights]. Map-type Default/Satellite radios
// have no icon aria-label so they're excluded by the same filter.
// "Tab aria-labels are localized ('Driving' -> 'Lái xe'), so we select by INDEX, not by label."
if (tab.disabled) → 'travel mode X is not available for this route'
```

## Data Shape
Tab-count wait: poll count of icon-carrying `button[role=radio]` until `> modeIdx` (≤12s) — "the mode tabs can lag the initial paint (the route duration may render before all 6 tabs are in the DOM)." A not-available tab still renders (disabled), so the wait also covers it.

## Decisive source
Comment block :275-286 quoted above (localization rationale + disabled detection). Post-click semantics :318-325: "After a real click the panel CLEARS (duration -> null) then repopulates with the new mode's duration, so we poll null -> non-null to wait out the re-render with no race against the previous mode's duration"; if still null after 15s the mode is unavailable — "The `disabled` property can lag the tab's render, so we detect unavailability from the absence of a route here instead." Flights special case (:287-288, :305-310): flight cards render OUTSIDE the Directions panel, so duration scope is the whole BODY while distance/via/label/tolls remain panel-scoped (flights have none). Duration leaf matcher excludes elements inside a radio (`inRadio` walk) so tab labels never masquerade as the route duration. Mode whitelist excludes motorcycle/ferry: "those aren't Maps tabs (motorcycling routes via driving; ferries are route segments)" (usage comment :34-36).

## Flow / Invariant
Select by structural position among icon-carrying radios; treat cleared-then-repopulated as the normal post-click sequence; verify availability by outcome (route exists), not by the possibly-lagging disabled attribute.

## Probe (direct tests)
gmaps smoke test pins cross-mode behavior live: London→Paris driving must NOT leak Eurostar's "2 hr 18 min" (`refuse "mode driving: transit leak"`), transit must return it, and an unavailable cycling route must exit non-zero with "not available for this route". Deterministic probe at pin: `grep -c "modeIdx" skills/gmaps/scripts/gmaps` → ≥4.

## Retrieve
grep-first (`modeIdx`, `role=radio`, `durScopeIsBody`).

## Verdict
ADOPT for any locale-varying tab strip: index-over-icon-radios + outcome-based availability is the portable contract.

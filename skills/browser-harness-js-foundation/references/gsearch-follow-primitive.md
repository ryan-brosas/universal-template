<!-- capsule-v2 -->
# gsearch follow Subcommand — the reusable open-and-read primitive

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
What is `gsearch follow`, and why does it exist as a first-class subcommand rather than ad-hoc code per consumer?

## Path / Symbol
`skills/gsearch/scripts/gsearch` :11-16 (purpose comment), :17-134 (whole subcommand), json-navigation.md citation :14-15.

## Signature
```bash
gsearch follow <url> [--selector S] [--json] [--settle MS] [--wait networkIdle|almostIdle|load]
# "Replaces hand-rolling the create-tab/navigate/wait/evaluate recipe for every result link."
# --json uses the poll-innerText recipe (application/json fires no Page lifecycle events and
# Chrome's JSON viewer is racy); see skills/cdp/interaction-skills/json-navigation.md.
```

## Data Shape
HTML mode: arm lifecycle wait (eventName mapped: load→'load', almostIdle→'networkAlmostIdle', else networkIdle) → navigate → wait → optional settle → extract `document.querySelector(S)?.innerText || document.body.innerText || ''`. Default selector `article, main, [role=main]`. URL scheme auto-repair: bare host gets `https://` prepended.

## Decisive source
Purpose comment :12-13 quoted above — this is the repo recognizing that its own search results begat a repeated follow-the-link pattern and promoting it to a shared primitive with flags for the three axes of variation (content selector / JSON-vs-HTML doctrine / readiness event). Validation-before-spawn applies here too: `--wait` whitelist, numeric `--settle`, missing-url usage errors (:21-52).

## Flow / Invariant
1. When two scripts copy the same CDP choreography, extract it as a subcommand of one.
2. Parameterize exactly the axes that vary (selector, wait event, settle, JSON mode) — nothing else.
3. Keep the JSON branch on the polling doctrine, citing the interaction-skill doc as its rationale.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "follow" skills/gsearch/scripts/gsearch` → ≥20; `grep -c "networkAlmostIdle" skills/gsearch/scripts/gsearch` → 1; live smoke possible via scripts/test on a networked host.

## Retrieve
grep-first (`follow`, `--settle`, `networkAlmostIdle`).

## Verdict
ADOPT the pattern-promotion move itself: shared CDP recipes become subcommands with narrow flags, documented against the interaction-skills corpus.

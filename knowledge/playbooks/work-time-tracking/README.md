---
title: work-time-tracking
summary: "Use when setting up, running, reviewing, or reporting tracked work time in any gig: installing or verifying the Pi work-time extension in a project, using the /work session clock, labeling tracked time by task for invoicing, reconciling user-attested sessions with automatic Pi-turn activity, producing hours drafts for timesheets or EOD reports, or diagnosing missing time records. Owns measurement mechanics and evidence discipline; never authorizes external writes or billing decisions by itself."
kind: playbook
---

# Work-time tracking

Two measures, kept separate at every step. **Session hours** (`/work start [label]` ... `/work stop`) are the explicit attested clock. **Tracked working hours** are the automatic record of agent work in the project root, not a measurement of all human work. Agree with the user how this measure may be reported. Nothing syncs anywhere automatically; hours enter the gig's canonical record only after the user confirms the draft, and the same time is never added twice.

## Deploy into a gig

Use the user's approved work-time extension implementation directory (labels.ts, ledger.ts, extension.ts, labels.test.ts, ledger.test.ts, extension.test.ts, README.md). This skill does not bundle that implementation. If its location is unknown, ask; if those files are missing, report that instead of improvising a replacement.

1. Copy the six code and test files into `<gig>/agents/time-tracking/`. The extension resolves the project root as two directories above its own file; place it accordingly.
2. Edit only the final `export default` line in `extension.ts` for this gig: `scopePrefix` (short slug used in record scopes), optional `legacyCommandNames`, and report `timezones` (IANA names). Adjust the label registry in `labels.ts` to this gig's invoice lines if they differ.
3. Merge `{"extensions": ["../agents/time-tracking/extension.ts"]}` into `<gig>/.pi/settings.json`.
4. Git-ignore the ledgers; they default to `<root>/exports/` (add `/exports/*` unless already ignored).
5. Verify code: `bun test agents/time-tracking` from the gig root. If bun is unavailable, report that rather than swapping runners.
6. Activate: in Pi at the gig root, the user approves project trust when prompted, then `/reload` or a new session. Do not grant trust on the user's behalf.
7. After one completed agent turn, `/work report` must show a Pi-activity line; otherwise diagnose before trusting anything.

## Daily use

- `/work start [label]`, `/work stop [note]`, `/work status`: the user-attested session clock. Labels normalize to registry keys when they match.
- Agent turns track automatically and each settled turn stores a draft task label derived from the request text and tool names (never the prompt text itself). Scheduled automations label themselves when their request mentions their domain or they use their characteristic tools.
- `/work time`: settled-turn totals and log path.
- `/work report [YYYY-MM-DD]`: per-day draft per configured timezone with per-label totals, written to `exports/work-report.md`; an optional date limits output to days on or after it.

## Evidence rules

- Session hours and tracked working hours are separate measures; never add the same time twice.
- Concurrent tabs overlap: report tracked hours as the wall-clock union of recorded intervals, never the raw per-turn sum. Per-label totals are per-stream coverage and may overlap each other across concurrent sessions.
- Labels are heuristic drafts from request text and tool names; review and correct them before invoicing. Records created before labeling was deployed stay unlabeled; reconstruct those separately and label the reconstruction as such.
- A capped silent gap is a floor, not a measurement. Days without interval records cannot be exactly deduplicated; label them legacy raw sums.
- An open session has Unknown end. Unknown is never zero.
- Ledgers hold metadata only (IDs, UTC timestamps, durations, labels); never prompts, file contents, customer data, or credentials. They are private (0600) and git-ignored.
- A killed process loses only the in-flight turn's open interval.
- External timers (Super Productivity) are optional manual backups; never double count a window the session clock already attests.

## Draft to official hours

1. Run `/work report`, then present per-day user-attested and per-label numbers separately, with every timezone labeled.
2. The user confirms the hours, the label split, and whether breaks were excluded.
3. The gig's designated record owner then appends the confirmed entry to its approved canonical store with basis labels: user-attested, timer evidence, or estimate. Resolve the actual destination from that gig's instructions; this skill supplies no client-specific location.
4. Never finalize billable totals without the user's confirmation.

## Failure modes

- No records at all: trust was declined or the extension is missing from `.pi/settings.json`; fix, then `/reload`.
- Start with no stop: the session is open or the process was killed; ask the user, never guess the end.
- Raw sums only: those days predate the interval ledger; label them accordingly.
- Wrong or missing labels: heuristics miss or misclassify; correct during review. Automation turns whose prompts never mention their domain may need a registry pattern or tool-pattern addition in `labels.ts`.

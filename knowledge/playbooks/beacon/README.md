---
title: beacon
summary: Use when driving the user's own logged-in Chrome through a browser-relay MCP server because no CDP endpoint is available - observe the page as text with stable node ids, bundle every act inside run, verify effects rather than acknowledgements, hand authentication to the user, and walk history with anchored scrolls.
kind: playbook
---

# Beacon, browser-relay skill

Beacon is a Chrome extension plus MCP relay that exposes the user's real,
logged-in browser to an agent: `observe` returns a tab roster and a compact
accessibility dump where each control carries an `n<id>`, and `run` executes
batched steps against those ids. There is no screenshot model and no selector
guessing - the dump is the map and the ids are the addresses. The host owns the
endpoint, key and config file; this procedure owns how to use the surface.

## When to Use / NOT

- **Use when:** the task needs the user's authenticated browser (their session,
  their cookies), no CDP endpoint is available, or the relay is the only browser
  surface wired into the host.
- **NOT when:** a CDP endpoint is available and preferred (`../cdp/README.md`);
  the page can be fetched over plain HTTP; or the work is read-only evidence
  capture that a simpler tool already answers.
- Authentication is never part of this surface: login, 2FA and consent steps
  answer `NEEDS_HUMAN` and belong to the user.

## Workflow

1. `observe({resetFocus:true})` for a full map (tab roster plus regions), then
   `observe({id})` or `observe({region})` to drill into a slice. Ids renumber
   after navigation, typing and re-render, so re-observe before addressing
   anything.
2. Target the tab: `navigate({tabId})` reuses an observed tab and
   `navigate({url})` reuses a same-host tab, opening a cross-site URL in a
   background tab so the user's own focus never moves. Tabs need not be visible.
3. Bundle every act inside `run` as a JSON steps array of
   `{tool, args, expect, commit}`. Single-act `click`/`type`/`press`/`scroll`/
   `focus`/`stroke` calls are refused with `SERIAL_ACT_DISABLED`; only
   `observe` and `navigate` work standalone. End a batch with proof
   (`expect.line`, `expect.url`, `expect.gen "+"`) so a missed step fails
   fast instead of drifting.
4. Verify the effect, not the acknowledgement: read the authority (response
   status, record count), then confirm identity with an independent query. A
   value reappearing in the dump can be the input field still holding it.
5. Re-observe between milestones (origin, destination, date, expanded panel).
   Ids in a list are not contiguous - the dump is a window, and gaps mean unseen
   items rather than absence.

## Verified surface behaviours

- **An acknowledgement is not an execution.** A bare `scroll({direction:'up'})`
  answers "Scrolled up" and moves nothing: `scroll` needs an explicit `id` or
  `ref` target, and a stale ref fails the whole batch
  (`NOT_FOUND: no unique target`). A refused single act also looks like a no-op
  when only the exception is inspected - read the response payload.
- **History walking in chat-style virtual lists.** Bundle about four anchored
  `scroll` steps plus a final `observe` in one `run`, then re-anchor from the
  latest dump because ids renumber. Judge progress by the window's oldest
  timestamp regressing; content or token diffs move on their own when the page
  is live. Consecutive batches without regression mean the loaded-history
  boundary, not slowness.
- **A form write may need a second click.** Controls that enable only after the
  field state commits can swallow the first click while still inert: retry once,
  then confirm by count or status rather than by the value being present.
- **Transient transport errors are recoverable.** `Connection closed`,
  `SSE error (405)` and `Already connected to a transport` clear with backoff;
  a 401 means a stale key, and "No browser connected" means the extension link
  is down rather than the endpoint.
- **Sessions stay human-owned.** The surface refuses credential entry by design:
  complete those steps by hand and resume on the authenticated session
  (`../security-and-hardening/README.md`).
- **One workflow built on this surface.** Harvesting a disposable-signup family from a
  notification feed and applying verified policy holds is owned by
  `../signup-abuse-response/README.md`.

## Verification

The claimed effect exists in the authority (status, record count, or membership
re-queried independently); movement was detected on an observable that only
movement can change; any write is reversible or its reversibility is stated;
and no credential reached the transcript.

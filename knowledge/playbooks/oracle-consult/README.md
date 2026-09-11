---
title: oracle-consult
summary: 'Use when the user asks to consult Oracle, ChatGPT, or an external model for a second opinion, plan review, or architecture decision - drive the @steipete/oracle MCP bridge or CLI end to end: tool discovery, engine fallback, file attachments, background runs, session polling, and transcript retrieval.'
kind: playbook
---

# Oracle Consult

## Purpose

An external-model consult that stalls on engine connection errors, missing API
keys, or unknown session mechanics wastes the review slot the user asked for.
The expensive parts are invisible until first use: browser mode attaches to a
debug-enabled Chrome instead of launching one, the API engine needs its own
provider key, and finished answers land in session artifacts, not stdout.

## When to Use / NOT

- **Use when:** the user asks to consult Oracle, ChatGPT, or an external model;
  a plan or diff needs a second opinion from a stronger model; multi-model
  fan-out is requested.
- **NOT when:** the task fits local tools (routing decisions still belong to
  you); Veda lanes are requested (`veda-lane` owns that CLI); web research
  alone suffices (web-search tools own that).

## Approach

1. **Discover before calling.** The MCP bridge exposes `oracle_consult`,
   `oracle_sessions`, and siblings. An invalid call is the cheapest schema
   probe: the error lists required parameters and accepted enums. Find the
   server through the MCP server list rather than assuming registration.
2. **Assemble the consult.** Put the full context in `prompt` (findings,
   constraints, questions, deliverable shape) and attach real files with
   `files` — absolute paths survive wrapper path resolution. Give a stable
   `slug`; it names the session directory for later retrieval.
3. **Expect engine fallback.** Default resolution is config → `api` when a
   provider key exists → `browser`. Browser mode needs a debug-enabled Chrome;
   `api` needs its provider key. On connection refusal, read the error: it
   names the port or key that is missing. If the oracle config sets
   `attachRunning: true`, either start Chrome with the debug port or flip that
   flag off for the run and pass `--copy-profile <user-data-dir>` so a private
   Chrome launches seeded with the signed-in profile; restore the config
   afterward. Prefer editing config only with a backup copy.
4. **Run long consults detached.** Browser consults run ten-plus minutes.
   Launch via the CLI (`oracle consult -p "$(cat prompt.md)" --file ... --slug
   ...`) under a supervisor writing a log, then poll the session directory:
   `meta.json` `status` flips to `completed`; the answer is in
   `artifacts/transcript.md` under the session slug.
5. **Deliver the answer, not the transcript.** Summarize the response against
   the questions asked, cite the conversation URL from the transcript, and note
   anything the model flagged as unverified. Verify model claims against source
   before treating them as fact.

## Boundaries

- Browser mode drives the user's signed-in ChatGPT and may briefly focus a
  visible automation window; say so when launching, and never run a consult the
  user did not request.
- Config edits (attach toggle, profile copy) are temporary: back up, restore,
  and verify the restore.
- Model output is a lead: verify plan claims against source and gates before
  implementing.

## Verification

- `meta.json` shows `completed`; `artifacts/transcript.md` exists and contains
  the answer; the reply cites the session/conversation link and the model used.
- Any temporary config change is restored and the restore is verified.

## References

- `oracle consult --help` / `oracle --help` for the installed CLI's flags.
- The MCP bridge's server tool list for wrapper-level discovery.

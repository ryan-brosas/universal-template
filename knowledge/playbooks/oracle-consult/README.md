---
title: oracle-consult
summary: 'Use when the user explicitly asks to consult Oracle, ChatGPT, or an external model: discover the installed tools, verify engine/profile behavior, run a bounded consult and retrieve its actual result without taking over the desktop.'
kind: playbook
---

# Oracle Consult

## Purpose

Run the external-model consultation the user requested, without confusing a
background runner with a non-disruptive browser. Preserve the selected model,
engine, account and data-sharing scope; a connection failure is not authority
to switch them or copy a signed-in profile.

## When to Use / NOT

- **Use when:** the user explicitly requests Oracle, ChatGPT or an external-model
  consultation, including a requested multi-model comparison.
- **NOT when:** local tools or ordinary web research answer the question, or when
  an unsolicited second opinion would upload context the user did not authorize.

## Approach

1. **Discover the live schema.** Inspect the configured Oracle MCP tools or the
   installed CLI's help; do not deliberately submit invalid calls for discovery.
   Tool names, model labels and browser controls can differ across installations.
2. **Prepare the bounded question.** Include the decision, useful findings,
   constraints and desired evidence. Attach only authorized files, never secrets.
   Use a stable session slug so a retry does not create duplicate consultations.
3. **Preview the execution boundary.** Use the tool's dry-run capability when
   available to inspect the resolved engine, model, profile and launch behavior
   before a real run. API mode needs no browser but still has provider cost and
   data-sharing implications; do not substitute it for a requested browser/model
   combination without permission.
4. **Keep browser mode off the user's desktop.** Prefer the already approved
   isolated/headless automation profile when the installed workflow supports it.
   Confirm actual launch/focus behavior; a private profile or detached process
   alone does not guarantee that no visible window activates. If the flow only
   supports a visible browser, ask for that specific exception before launching.
   Missing login, 2FA or debugging consent is `NEEDS_HUMAN`, not permission to
   copy cookies/profile data, toggle attach settings or relaunch a personal browser.
5. **Supervise long runs.** Consults may take many minutes. Use the installed
   session/status facilities or a bounded detached job, retain its identifier and
   observe completion without repeatedly starting consultations. A client timeout
   does not prove generation stopped; inspect the existing run before retrying.
6. **Deliver the result.** Inspect the completed session and actual answer artifact.
   Summarize it against the requested question, cite its session/conversation when
   available, and distinguish source-backed findings from model suggestions.

## Boundaries

- A consultation request permits that scoped consultation, not desktop focus,
  credential copying, provider/model changes or additional unrequested consults.
- Use a visible browser only with explicit permission. Authentication and consent
  stay human-owned; never simulate approval keystrokes to make a run unattended.
- Do not edit host configuration as an automatic fallback. An authorized change
  needs a private backup, exact scope, verification and a restoration plan.
- Model output is advisory. Verify decisive claims against current source and tests.

## Verification

- Establish completion through the installed runner's actual status and answer;
  a launch acknowledgement, quiet log or connected browser is not completion.
- Report the model/engine used, the answer and any unresolved coverage limits.
- Verify isolation/focus behavior separately from answer quality. If it could not
  be established, report that limit rather than promising unattended operation.
- Restore and verify any separately authorized temporary configuration change.

---
name: black-box-experience-review
description: "Use when reviewing an app as a black box for observable experience failures across journeys, seams, states, and recovery before shipping or after changes."
disable-model-invocation: true
license: MIT
metadata: '{"source":"close adaptation: browserbase/skills ui-test (MIT, verified via DeepWiki; skills/ui-test/SKILL.md, references/ux-heuristics.md, references/adversarial-patterns.md); synthesis: antigravity-awesome-skills (MIT) api-onboarding, sdk-dx, ux-copy, e2e-testing-patterns; concepts only: plugin87/ux-ui-agent-skills severity taxonomy (license unverified, discovery evidence)"}'
---

# Black-Box Experience Review

## Core Principle

The app is a black box: evidence comes from observable behavior, never from source-code assumptions.

## When to Use

Use when an app must be checked before shipping or after changes, and the
question is whether real users can complete real work across happy paths and
failure paths. The app is a black box: evidence comes from observable behavior,
never from source-code assumptions.

## When NOT to use

- Mapping journeys and seams first -> app-experience-mapping
- Screen-level UI review -> ux-review
- Visual styling or design tokens -> design-taste-frontend / design-system-audit

## Workflow

1. Functional round: walk each core journey end to end; the next action must be discoverable at every step.
2. Adversarial round: break each seam (unauthorized access, expired sessions, offline start, network loss mid-task, partial input, destructive actions without confirmation).
3. Coverage gaps: sweep every journey at narrow viewport and across channels.
4. State checks at every seam: loading, empty, partial, error, success.
5. Persistence and resumability: interrupted tasks resume where they stopped.
6. Handoffs and channels: return path works, partial failures recover, no state lost in transit.
7. Rate severity (Critical/Major/Minor/Enhancement) and issue the verdict: Pass, Needs Improvement, or Fail.

## Source-code independence

Do not infer behavior from code. Drive the app as a user and record what is
observable: screens, controls, states, timing, messages, and recovery paths.
Use the platform's browser or runtime tools (browser-tools, playwright,
chrome-devtools) with no external testing service or credentials.

## Review rounds

1. Functional: map core journeys (entry, action, feedback, completion) and
   walk each end to end. The next action must be discoverable at every step.
2. Adversarial: break each seam. Unauthorized access, expired sessions,
   revoked roles, shared links, offline start, network loss mid-task,
   partial input, invalid data, missing routes, cancelled external handoffs,
   and destructive actions without confirmation.
3. Coverage gaps: sweep every journey at narrow viewport and across channels
   (web, mobile, desktop, CLI, API where applicable), checking navigation,
   back behavior, and dead ends.

## State checks

At every seam verify loading, empty, partial, error, and success states.
Failures must preserve user input, explain the problem in plain language,
offer retry or recovery, and never expose technical errors. Loading must not
cause layout shift; success must not be silent.

## Persistence and resumability

Fill a form halfway, navigate away, and return: input must survive or be
restored with a clear path. Interrupt a task (background, refresh, app
switch): the session must resume where it stopped, and an expired session
must return the user to the interrupted location after sign-in.

## Handoffs and channels

For every external handoff (payments, OAuth, file pickers, deep links,
notifications, background jobs) verify: the user is told what is happening,
the return path works, partial failures recover, and no state is lost in
transit. Check the same intent across channels for continuity.

## Severity and verdict

Rate findings Critical (blocks the journey), Major (serious friction this
release), Minor (polish), Enhancement (backlog). Every finding carries
evidence: screen, control, step, observed behavior, console or runtime
output, viewport width, exact copy, and the user blocked. Verdict: Pass,
Needs Improvement, or Fail. Any Critical finding makes the verdict Fail.

## Red Flags

- Failures that lose user input.
- Technical errors exposed to users.
- Silent success or layout shift on loading.
- Findings without evidence.
- Any Critical finding with a verdict other than Fail.

## Verification

Every finding carries evidence: screen, control, step, observed behavior, console or runtime output, viewport width, exact copy, and the user blocked. Verdict Pass/Needs Improvement/Fail; any Critical finding makes the verdict Fail.

## Skill Result Contract

```
<skill_result>
  <skill>black-box-experience-review</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Findings with screen, step, observed behavior, runtime output, viewport, exact copy</evidence>
  <artifacts>Severity-rated findings and verdict: Pass, Needs Improvement, or Fail</artifacts>
  <risks>Critical finding under-rated, coverage gaps, or none</risks>
</skill_result>
```

## References

N/A — no reference files; this skill is self-contained.

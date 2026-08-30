<!-- capsule-v2 -->
# Task notification XML contract & pill grammar — what exact shape must a task_notification carry, and how do UI labels derive without stored state?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What are the XML tags, escape rules, and status-tag omission semantics every task type's notification must respect — and how is the footer-pill label computed?

## Tag set + escapeXml + monitor-vs-bash prefixes; label = pure function of task array
**Path/Symbol:** `src/constants/xml.ts` tags (`TASK_NOTIFICATION_TAG`, `TASK_ID_TAG`, `TOOL_USE_ID_TAG`, `OUTPUT_FILE_TAG`, `STATUS_TAG`, `SUMMARY_TAG`, `TASK_TYPE_TAG`, plus remote-only `REMOTE_REVIEW_TAG`/`ULTRAPLAN_TAG`/`WORKTREE*`); emitters in LocalShellTask.tsx:105-172, LocalAgentTask.tsx:197-262, LocalMainSessionTask.ts:224-263, RemoteAgentTask.tsx:166-239; `src/tasks/pillLabel.ts` (whole :1-82): `getPillLabel`, `pillNeedsCta`.
**Signature:** `getPillLabel(tasks: BackgroundTaskState[]): string`.
**Data Shape:** notification = `<task_notification><task_id>…</task_id>[<tool_use_id>…</tool_use_id>][<task_type>…</task_type>]<output_file>…</output_file>[<status>…</status>]<summary>…</summary>[extras]</task_notification>` + optional free-text body AFTER the closing tag (remediation advice / review content). Summaries share the `Background command ` prefix constant so the UI collapse transform recognizes them; monitors use distinct "Monitor …" wording "so Monitor completions don't fold into the 'N background commands completed' collapse".

### Decisive source
```xml
<TASK_NOTIFICATION_TAG>
<TASK_ID_TAG>{taskId}</TASK_ID_TAG>{toolUseIdLine}
<OUTPUT_FILE_TAG>{outputPath}</OUTPUT_FILE_TAG>
<STATUS_TAG>{status}</STATUS_TAG>
<SUMMARY_TAG>{escapeXml(summary)}</SUMMARY_TAG>
</TASK_NOTIFICATION_TAG>
```
All summary interpolations go through `escapeXml`. The stall watchdog emits NO `<status>` tag at all (see task-stall-watchdog). Pill: all-same-type switch → local_bash splits shells vs monitors by `kind`; in_process_teammate counts DISTINCT teamNames ("1 team"/"N teams"); ultraplan singletons render ◇ open diamond while running and ◆ filled only at plan_ready; mixed types fall to "N background tasks". `pillNeedsCta` is true ONLY for a single ultraplan task with an undefined≠running phase.

**Flow:** any terminal/stall event → per-type emitter builds XML with the shared tag constants → enqueuePendingNotification(mode 'task-notification') → model-side parser keys on tags; UI collapse transform keys on the prefix.
**Invariant:** Summary text MUST be escaped (descriptions come from user commands); the `Background command ` prefix is load-bearing for folding; omitting `<status>` signals non-terminal informational notifications; priority differs by kind ('next' for monitor/stall, default later for bash completions).
**Probe:** `grep -n 'BACKGROUND_BASH_SUMMARY_PREFIX =' src/tasks/LocalShellTask/LocalShellTask.tsx` (:23) and `grep -n 'fold into' src/tasks/LocalShellTask/LocalShellTask.tsx` (:132) and `grep -n '1 team' src/tasks/pillLabel.ts` (:35).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "enqueuePendingNotification task-notification", limit: 5 });
```

## Verdict
Adopt the tag vocabulary + escaping + prefix-folding contract verbatim if porting the notification channel. Adapt wording freely. Omit diamond glyphs unless you carry ultraplan phases.

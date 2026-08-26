<!-- capsule-v2 -->
# Event parse gate — how do untrusted JSONL lines become validated events without ever leaking protected ones into memory-visible output?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** a porter must decide where privacy filtering happens — after collection, at storage, or at read — and what shape invalid input takes.

## Parse-time rejection of malformed AND protected records
**Path/Symbol:** `src/main/activity-event-file.ts:parseActivityEvent` (96-102), `:parseRawActivityEvent` (104-113), `src/main/privacy-policy.ts:isProtectedActivityEvent` (135-152).
**Signature:** `parseActivityEvent(line: string, options?: ActivityPrivacyOptions): ActivityEvent | undefined`.
**Data Shape:** one JSONL line in; a zod-validated `ActivityEvent` (`version: 1` literal, id ≤ 128 chars, ISO-Z regex timestamp, enum of 17 kinds, per-field bounded strings, arrays capped e.g. `visibleText.max(100)`) or `undefined`. There is no third "rejected" value and no error channel.

### Decisive source
```ts
export function parseActivityEvent(
  line: string,
  options: ActivityPrivacyOptions = {}
): ActivityEvent | undefined {
  const event = parseRawActivityEvent(line);
  return event && !isProtectedActivityEvent(event, options) ? event : undefined;
}
```
`parseRawActivityEvent` returns `undefined` for lines over `MAX_EVENT_LINE_CHARACTERS = 256 * 1_024`, JSON failures, and any `activityEventSchema.safeParse` failure. `isProtectedActivityEvent` is a pure predicate ladder: always-protected bundle ids → messaging bundles/browser observations unless `captureMessagingActivity` → mail bundles/mail domains/mail window titles unless `captureEmailActivity` → sensitive text fields combined with `focused_element_changed | text_input | document_changed`.

**Flow:** line → size gate → JSON.parse → zod safeParse → protected-predicate → event | undefined. Both malformed and private input collapse into the same `undefined`, so downstream code cannot accidentally special-case "private but present".
**Invariant:** no code path returns a protected event; capture flags default to false, so privacy is opt-IN, never opt-out.
**Probe:** `src/main/activity-event-file.test.ts:12-34` ("rejects unknown kinds, invalid timestamps, and oversized records" — unknown kind, non-ISO date, 256KiB+1 line, bad nested array item, >100 items all → `undefined`) and `36-105` (mail/messaging events excluded by default, included only with the flag; 1Password stays protected even with messaging enabled). Runner note: this file's suite is blocked in this environment by missing `node_modules` (zod unresolvable); the assertions were verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "parse activity event protected schema", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the collapse-to-undefined parse gate and default-off capture flags for any ingest path touching sensitive content; adapt the specific bundle-id/domain lists to your platform; omit macOS bundle identifiers. Coverage: both files checked via `check_index_coverage` → `no_recorded_issue`, generation matches pin.

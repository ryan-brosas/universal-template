<!-- capsule-v2 -->
# Activity event prefs codec — what happens when a stored notification-preferences row is corrupt or shaped by an older version?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How is the JSONB prefs column validated on read, and what does the reader get when validation fails?

## Closed-key event taxonomy + lenient safeParse-over-defaults read
**Path/Symbol:** `apps/web/src/features/notifications/schema.ts:activityEventTypes` / `notificationPreferencesSchema` (lines 6–16); reader `apps/web/src/features/notifications/data.ts:parsePrefs` + `getNotificationPreferences` (lines 9–26); defaults `apps/web/src/features/notifications/constants.ts` (lines 3–6).
**Signature:** `parsePrefs(prefs: unknown): NotificationPreferences`; `getNotificationPreferences(userId): Promise<NotificationPreferences>`.
**Data Shape:** `activityEventTypes = ["poll.response.submitted", "poll.comment.added"]` — naming convention `{entity}.{sub-entity}.{past-tense-verb}` documented at the const; prefs = closed-key record of those keys → boolean; defaults are both `true`.

### Decisive source
```ts
export const activityEventTypes = [
  "poll.response.submitted",
  "poll.comment.added",
] as const;

/**
 * Activity event type naming convention: {entity}.{sub-entity}.{past-tense-verb}
 */
export const notificationPreferencesSchema = z.record(
  z.enum(activityEventTypes),
  z.boolean(),
);
```
```ts
function parsePrefs(prefs: unknown): NotificationPreferences {
  const parsed = notificationPreferencesSchema.safeParse(prefs);
  return {
    ...defaultNotificationPreferences,
    ...(parsed.success ? parsed.data : {}),
  };
}
```

**Flow:** any read of prefs goes through safeParse → success: defaults spread first, stored values override per key → failure (corrupt JSON, wrong value type, or ANY key outside the enum — zod v4 keyed records reject unrecognized keys, so one legacy key invalidates the WHOLE record): the parse result is discarded and the caller silently gets the all-on defaults. There is no error path, no logging, and no partial salvage.
**Invariant:** reads can never throw on bad data, but the recovery granularity is all-or-nothing: a single unknown key re-enables every notification for that user (defaults are all `true`). A porter who wants per-key tolerance must switch to `z.looseObject`/per-key fallbacks deliberately — and accept that then removed event types linger forever.
**Probe:** deterministic grep anchors (executed): `grep -n 'safeParse' apps/web/src/features/notifications/data.ts` → line 10; `grep -c 'true' apps/web/src/features/notifications/constants.ts` → 2 (both defaults enabled). No dedicated upstream test for the codec.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_code({ project: "rallly", pattern: "notificationPreferencesSchema", path_filter: "features/notifications", limit: 5 });
```
(BM25 `search_graph` on the schema identifiers totals 0 at this generation — use the text-search form above.)

## Verdict
Adopt the event-type vocabulary contract (`{entity}.{sub-entity}.{past-tense-verb}`) and the never-throw read verbatim; adapt the fail-granularity decision to your product (all-on vs all-off vs per-key) consciously; omit nothing — this file is the whole codec. See also `notification-preference-jsonb-merge` for the write side of the same column.

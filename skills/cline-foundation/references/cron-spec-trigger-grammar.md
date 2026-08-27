<!-- capsule-v2 -->
# cron-spec-trigger-grammar — how does a TOLERANT Markdown trigger grammar scope fields by trigger kind instead of a vocabulary?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When unknown user fields must not hard-fail automation specs, how do you keep cross-kind mistakes loud while everything else degrades silently?

## Trigger-kind exclusivity tables; tolerant normalizers; two throwing vocabularies; order-immune hash over RAW body
**Path/Symbol:** `sdk/packages/core/src/cron/specs/cron-spec-parser.ts` (`parseCronSpecFile` :258-489; `inferTriggerKindFromPath` :28-39; tables :204-213; `stableStringify` :169-183; `computeContentHash` :185-194; `splitFrontmatter` :41-58).
**Signature:** `parseCronSpecFile({relativePath, raw}): CronSpecParseResult` — never throws; `{externalId, relativePath, triggerKind, body, contentHash, spec? , error?}`.
**Data Shape:** Trigger kind comes from the PATH, not content: `events/` prefix AND `.event.md` suffix ⇒ event; any `*.cron.md` ⇒ schedule; else one_off. SCHEDULE_ONLY = [schedule, timezone]; EVENT_ONLY = [event, filters, debounceSeconds, dedupeWindowSeconds, cooldownSeconds, maxParallel]; REMOVED = [cwd]. Defaults: mode "yolo", enabled true, source "user", title fallback filename stem.

### Decisive source
```ts
if (triggerKind !== "schedule") { for (const key of SCHEDULE_ONLY_FIELDS) if (frontmatterData[key] !== undefined)
	return invalidWithHash(..., `field "${key}" is only allowed on *.cron.md specs`); }
for (const key of REMOVED_FIELDS) if (frontmatterData[key] !== undefined)      // cwd removed BETWEEN the two tables
	return invalidWithHash(..., `field "${key}" is no longer supported; cron specs use workspaceRoot as cwd`);
if (triggerKind !== "event") { for (const key of EVENT_ONLY_FIELDS) ... }
// Tolerant normalizers return undefined for junk (normalizeMode/Tags/StringList/
// asPositiveInt/asNonNegativeInt) EXCEPT closed vocabularies that throw INSIDE a
// caught boundary: normalizeToolList (∈ ALL_DEFAULT_TOOL_NAMES), normalizeExtensions
// (∈ rules|skills|plugins).
// Hash twin divergence vs tasks/specs: stableStringify key-sorts objects and drops
// undefined recursively, then hashes body RAW (untrimmed); splitFrontmatter returns
// the RAW un-normalized body when frontmatter is missing (:47/:52) — the task twin
// returns its CRLF-normalized body and hashes insertion-order JSON over trimmed body.
```

**Flow:** path→kind ⇒ splitFrontmatter ⇒ YAML map check (catch/non-map ⇒ invalid with `{}`-hash) ⇒ hash over data+RAW body ⇒ schedule-only veto ⇒ removed-cwd veto ⇒ event-only veto ⇒ prompt required (frontmatter `prompt` ?? trimmed body) ⇒ workspaceRoot required ⇒ tools/extensions (throwing vocabs, caught) ⇒ explicit-invalid mode errors else silent normalize ⇒ per-kind assembly: schedule requires schedule+timezone through `validateCronSchedule` (caught), event requires `event`, else one_off.
**Invariant:** Cross-kind field placement is ALWAYS an error (loud), while unknown extra fields and malformed optionals never fail the file (tolerant) — except the two security-relevant vocabularies (tools/extensions) which fail loudly inside a result, never as a throw. Failures still carry the RAW-body hash so the reconciler can persist `parse_status='invalid'`.
**Probe:** `grep -cF 'is no longer supported; cron specs use workspaceRoot as cwd' sdk/packages/core/src/cron/specs/cron-spec-parser.ts` → 1 (:319); `grep -cF 'return { frontmatter: undefined, body: raw };' …cron-spec-parser.ts` → exactly 2 (:47,:52). Test pins (`cron-spec-parser.test.ts`, 23 cases read whole): "does not classify *.event.md outside events/ as event" (:19), "preserves explicit empty tools and extensions lists", "rejects removed cwd field", computeContentHash "is stable under key order", "records parse error without throwing".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.cron.specs.cron-spec-parser.parseCronSpecFile" });
// observed: Function lines 258-489 verbatim, byte-equal to the checkout whole-read
```

## Verdict
Adopt kind-scoped exclusivity tables over vocabularies when users author trigger files, tolerant-normalizer ergonomics with loud closed vocabularies, stableStringify hashing for order-immune drift detection, and parse-errors-as-data. Adapt kind names, tables, and cron validation. Omit Cline's scheduler internals. Coverage: no_recorded_issue both paths @ gen 2026-08-24T16:12:41Z; runner-BLOCKED honestly.

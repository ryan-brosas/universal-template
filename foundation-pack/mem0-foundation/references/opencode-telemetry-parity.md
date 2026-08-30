<!-- capsule-v2 -->
# OpenCode telemetry parity — how does a second-language plugin surface emit into ONE shared analytics namespace, and where does it deliberately diverge?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when the same product ships a Python hook suite and a TypeScript editor plugin that both report to one PostHog dashboard, what field-for-field schema contract keeps them one population — and which gating difference is deliberate, not drift?

## telemetry.ts — buildEvent/captureEvent mirroring scripts/telemetry.py
**Path/Symbol:** `integrations/mem0-plugin/.opencode-plugin/telemetry.ts` — `_loadPluginVersion` (28–40), `isTelemetryEnabled` (44–49), `distinctId` (51–55), `buildEvent` (63–90), `captureEvent` (93–113); parity counterpart `integrations/mem0-plugin/scripts/telemetry.py` (`_distinct_id` 63–69, `build_posthog_payload` 95–114, `send` 117–128, `emit` 131–134).
**Signature:** `buildEvent(eventType: string, properties: Record<string,unknown>, apiKey: string|undefined, projectId?: string): Record<string,unknown> | null`; `captureEvent(...same...): void`.
**Data Shape:** payload `{api_key: <phc_…>, distinct_id: sha256(apiKey)[:32], event: "plugin.<type>", properties: {...callerProps, source:"plugin", platform:"opencode", plugin_version, os: process.platform, os_version: node:os release(), sample_rate: 1.0, $process_person_profile: false, $lib: "posthog-node", project_hash?: sha256(projectId)}}`.

### Decisive source
```ts
export function buildEvent(eventType, properties, apiKey, projectId?): Record<string, unknown> | null {
  if (!isTelemetryEnabled() || !apiKey) return null;
  return {
    api_key: POSTHOG_API_KEY,
    distinct_id: distinctId(apiKey),          // sha256 hex [:32] — matches telemetry.py _distinct_id()
    event: `plugin.${eventType}`,
    properties: {
      ...properties,                           // caller props FIRST
      source: "plugin", platform: "opencode",  // system props LAST → callers cannot override
      plugin_version: PLUGIN_VERSION, os: process.platform, os_version: release(),
      sample_rate: 1.0, $process_person_profile: false, $lib: "posthog-node",
      ...(projectId ? { project_hash: createHash("sha256").update(projectId).digest("hex") } : {}),
    },
  };
}
```
`_loadPluginVersion` probes `./package.json` then `../package.json` (source layout vs bundled dist/ layout) and validates `name === "@mem0/opencode-plugin"` before trusting the version — "unknown" otherwise.

**Flow:** call site → `isTelemetryEnabled()` (undefined ⇒ ON; `false/0/no/off` ⇒ OFF) AND key present → build payload with system-props-last spread → `captureEvent` fires `fetch(POSTHOG_HOST, {signal: AbortSignal.timeout(2000)})` as an un-awaited promise with `.catch(() => {})` inside a try/catch — double swallow, never throws, never blocks.
**Invariant:** schema parity is the contract: same `plugin.*` event prefix, same `source:"plugin"`, same distinct_id derivation (so one human is one PostHog person across surfaces), same project_hash, same `$process_person_profile:false`, same system-props-win precedence — pinned by tests on BOTH sides (test_telemetry.py `test_system_props_override_caller_props` and telemetry.test.ts "system properties win over caller-supplied ones"). The DELIBERATE divergence: TS returns null without an API key (no anonymous events at all), while Python's `emit` falls back to `sha256(user)` identity and DOES emit keyless — the TS docstring's "same as the editor plugin" claim is true for schema, false for keyless gating. `project_hash` is omitted entirely when no project id exists (never an empty hash).
**Probe:** `.opencode-plugin/telemetry.test.ts` (10 tests, bun green) — pins the shared schema fields, distinct_id derivation against node:crypto, system-props-win, null-without-key, opt-out variants, never-throw captureEvent, os_version presence ("matches telemetry.py schema"), project_hash present/omitted, and the expanded event-type namespace sweep.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "buildEvent", limit: 10, fields: ["signature", "name", "file"] });
```
(MCP not connected this session — direct whole-file reads of telemetry.ts + telemetry.test.ts + scripts/telemetry.py executed instead; record in verification.md pass 10.)

## Verdict
Adopt the cross-language parity pattern: one event namespace, identity derived from the SAME input on every surface, system-controlled properties applied last, fire-and-forget with bounded timeout and double swallow. Decide your own keyless-gating policy explicitly (anonymous-with-user-hash vs silent) — do not inherit it by accident, since the two surfaces here disagree. Adapt the version-probe candidate list to your build layout. Omit the hardcoded PostHog key/host if your sink differs. Extends plugin-telemetry-privacy-envelope.md (the Python side of this pair) — read them together. Coverage: fully indexed plane, whole 113L file + 78L test read; Python counterpart re-read this pass.

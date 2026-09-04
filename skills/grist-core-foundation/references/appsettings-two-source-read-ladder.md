<!-- capsule-v2 -->
# AppSettings two-source read ladder — in what order does a setting resolve across process env and DB-stored env vars, and what provenance survives a failed lookup?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the resolution order and failure posture of `AppSettings.read()` across environment sources, and how must a porter preserve the diagnostics/censor contract?

## Read env first, then root's db stack; record provenance even when nothing is found
**Path/Symbol:** `app/server/lib/AppSettings.ts` — `class AppSettings` (:11–311), core method `read(query)` (:81–129); singleton `export const appSettings = new AppSettings("grist")` (:316); helper `getEnvVarsFromQuery` (:387–390).
**Signature:** `read(query: AppSettingQuery): this`; typed wrappers `readString/readBool/readInt/readFloat` + `require*` twins that throw `` `missing environment variable: ${query.envVar}` ``.
**Data Shape:** `AppSettingQuery = { envVar: string | string[], preferredEnvVar?, defaultValue?, censor?, acceptedValues? }` (numbered variant adds `minValue/maxValue`). Result provenance `_info = { found, envVar, source: "env"|"db", query }`. Values are JSON-like (`JSONValue` union :394). Root-only `_envVars` stack is set via `setEnvVars()` which THROWS if called on a child (:28–32) — DB-sourced settings ride the ROOT object only.

### Decisive source
```ts
// AppSettings.ts:93-110 — the two-source precedence ladder
const sources = [{ name: "env", vars: process.env }];
if (this._root._envVars) {
  sources.push({ name: "db", vars: this._root._envVars });
}
let envVar = envVars[0];
for (const { name, vars } of sources) {
  for (const synonym of envVars) {
    value = vars[synonym];
    if (value !== undefined) { envVar = synonym; found = true; source = name as any; break; }
  }
  if (found) { break; }
}
```

**Flow:** `read()` resets value+info → builds source list [process.env, root._envVars?] → scans source-major then synonym-major (first source wins entirely; within a source, first listed synonym wins) → records `_info` REGARDLESS of success → falls back to `defaultValue` only when nothing found → `acceptedValues` mismatch throws even for defaulted values.
**Invariant:** Provenance is written on FAILURE too (`_info.found=false`) — `describeAll()` can report "would find in env var X" for unset flags because the QUERY survived, not the value. A porter who clears state on miss breaks the `/api/config` UI's "how is this configured" reporting. Censoring happens ONLY at describe-time (`describe()` :280–289 prints `"*****"` when `query.censor && value !== undefined`) — the raw secret stays readable on the node object; never censor at read time or config dry-runs (ConfigBackendAPI reads secrets back) break.
**Probe:** `test/server/lib/AppSettings.ts` (min/max range throws :20–33, NaN throw message "does not look like a number" :34–37, non-finite default throw :39–45, default-within-range returns 5 :58–65). Source pins: `grep -c '"db"' app/server/lib/AppSettings.ts` = ≥2 (:86 type, :95 push); `grep -n '\*\*\*\*\*' app/server/lib/AppSettings.ts` = :283.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"AppSettings read requireString section flag describe","limit":10,"detail":"ids"}'
```

## Verdict
Adopt the two-source precedence ladder, provenance-on-failure, describe-time censoring, and the root-only env-stack rule; adapt the JSON-source note ("keep JSON-like in case we load from JSON", :392–393) to your storage; omit grist's specific flag vocabulary. Direct mocha coverage exists at this pin (AppSettings.ts suite); runner-blocked locally (repo toolchain not installed) — probes recorded as source-pinned assertions.

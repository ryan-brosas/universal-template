<!-- capsule-v2 -->
# Memory discovery — session enumeration and scope resolution

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does a memory provider find sessions and resolve a scope (session/project/global) into concrete files, newest-first, bounded?

## Connected graph-selected seam
**Path/Symbol:** `src/memory/discovery.ts` (164 lines): `encodeCwdDir` (:26-27), `enumerateAllSessions` (:73-92), `resolveSessionTarget` (:114-128), `resolveScope` (:139-164), `AmbiguousSessionError` (:102-112).
**Signature:** `resolveScope({agentDir, cwd, scope, sessionId?, sessionFile?, maxSessions})` — scope `session` (default, current/newest for cwd), `project` (all under cwd dir), `global` (all, bounded), `session:<id-or-path>` (one specific).
**Data Shape:** `SessionRef {id, file, cwd, mtime}`; session files stored under `agentDir/sessions/--<encoded-cwd>--/*.jsonl`; `encodeCwdDir` encodes a cwd into a safe dir name (`--` + resolved path with `/`/`\`/`:` replaced by `-` + `--`).

### Decisive source
```ts
export const encodeCwdDir = (cwd) => `--${path.resolve(cwd).replace(/^[/\\]/, "").replace(/[/\\:]/g, "-")}--`
// enumerateAllSessions: newest first by file mtime, bounded by maxSessions
return files.map(refFromFile).sort(compareRefsByRecency).slice(0, Math.max(1, maxSessions))
// resolveScope: session (default) / project / global / session:<id-or-path>
```

**Flow:** `resolveScope` maps a scope string to concrete session files: `session` = current or newest for cwd; `project` = all under the cwd's session dir; `global` = all, bounded by `maxSessions`; `session:<id-or-path>` = one specific (resolved by id or exact path, throwing `AmbiguousSessionError` when an id matches multiple). Enumeration is newest-first by mtime, bounded.
**Invariant:** an ambiguous session id throws `AmbiguousSessionError` (never silently picks one); enumeration is bounded by `maxSessions`; cwd is encoded into a safe dir name.
**Probe:** `tests/` memory coverage (encodeCwdDir encoding; enumerate newest-first + bounded; resolveScope session/project/global; ambiguous id throws).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "resolveScope enumerateAllSessions encodeCwdDir session project global", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the session-discovery + scope-resolution model (session/project/global, newest-first, bounded, ambiguity-guarded); adapt the session dir layout and scope vocabulary to host.

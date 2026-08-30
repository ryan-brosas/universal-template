<!-- capsule-v2 -->
# Skill catalog URL pull — how do you ingest a remote skill catalog without traversal or origin escape?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does a URL-registered skill source become local directories without letting a hostile index escape the cache or fetch cross-origin files?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/skill/discovery.ts`: `pull` (:127-213), `isSafeSegment` (:14-21), `isSafeRelativePath` (:23-51), `download` (:78-90), staging swap (:168-198).
**Signature:** `pull: (url: string) => Effect.Effect<AbsolutePath[]>`.
**Data Shape:** index JSON `{skills: [{name, version?, files: string[]}]}` decoded via Schema; cache root `<global.cache>/skills/<Bun.hash(base).toString(16)>`; per-skill root `<cacheRoot>/<name>`; returns only directories containing an entrypoint.

### Decisive source
```ts
if (!isSafeSegment(skill.name)) return []
if (!skill.files.includes("SKILL.md") && !skill.files.includes(`${skill.name}.md`)) return []
...
if (!isSafeRelativePath(file)) return undefined
...
if (resource.origin !== source.origin) return undefined
const destination = path.resolve(root, file)
if (!FSUtil.contains(root, destination) || destination === root) return undefined
```
Any violation drops the WHOLE skill (empty array), not just the offending file — and the test proves rejection happens before any file fetch:
```ts
test("rejects file traversal without fetching files", async () => {
  const result = await pull([{ name: "deploy", files: ["SKILL.md", "../outside.md"] }])
  expect(result.requests).toEqual([`${base}index.json`])
```

**Flow:** fetch `index.json` (retryTransient ×2, exponential 200ms jittered, filterStatusOk; failure → log + `[]`) → per skill (concurrency 4): validate name/files/origin/containment → versionless or unchanged-version skills download files individually (per-file exists short-circuit, concurrency 8) → version-CHANGED skills stage a full swap: download into `<root>.tmp-<uuid>`, require entrypoint present, write `.opencode-version`, then `Effect.uninterruptible` rename root→backup, staging→root (restore backup on rename failure), remove backup; staging always removed in `ensuring` → publish root only if the entrypoint exists.
**Invariant:** a hostile index can never (a) fetch a file outside the index origin, (b) write outside the per-skill cache root, (c) leave a partially-updated skill directory (staging swap is all-or-nothing), or (d) trigger any file request for a rejected skill.
**Probe:** `packages/core/test/skill-discovery.test.ts` (7 tests: 4 rejection cases pinning `requests == [index.json]` only + empty cache dir; nested-file download; version-change refresh; stale-file removal after swap — old files survive a failed partial update, disappear after a successful one).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SkillDiscovery pull index.json isSafeRelativePath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whole-skill fail-closed validation before any fetch, same-origin file URLs, contains() containment on skill root AND file destinations, and the uninterruptible staging swap for versioned updates. Adapt the cache-key hash and entrypoint naming to your host. Omit Bun/Effect specifics. Coverage caveat: all seven behaviors are pinned by the direct test; no graph coverage check ran this session (MCP not connected).

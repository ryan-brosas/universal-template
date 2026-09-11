<!-- capsule-v2 -->
# Atomic privacy scrub — how do you physically delete protected records from shard files without corrupting them or losing malformed evidence?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** a porter must decide whether retroactive deletion rewrites in place, and what happens to lines the current schema can no longer parse.

## Pid-tagged 0600 temp file + rename rewrite, preserving unparsable lines verbatim
**Path/Symbol:** `src/main/activity-event-file.ts:scrubProtectedActivityEvents` (138-176).
**Signature:** `scrubProtectedActivityEvents(dataDirectory: string, options?: ActivityPrivacyOptions): number` — returns count of removed events; readdir failure → `0`.
**Data Shape:** reads every shard line as raw string; emits kept raw strings; one atomic rename per changed file.

### Decisive source
```ts
const event = parseRawActivityEvent(line);
if (!event) return [line];                       // malformed evidence is preserved verbatim
const filtered = privacyFilter.filter([event]);
if (filtered.length === 1 && filtered[0] === event) return [line];
changed = true;
removed += 1;
return filtered.map((candidate) => JSON.stringify(candidate));
...
const temporaryPath = `${path}.privacy-scrub-${process.pid}`;
writeFileSync(temporaryPath, kept.length ? `${kept.join("\n")}\n` : "", { mode: 0o600 });
chmodSync(temporaryPath, 0o600);
renameSync(temporaryPath, path);
eventFileCache.delete(path);
```

**Flow:** per file: split on `\n` → keep blank/malformed lines untouched → filter each parsed event through the SAME stateful `ActivityPrivacyFilter` used at read time → if anything changed, write a fresh file under `${path}.privacy-scrub-${process.pid}` with mode 0600 (belt-and-braces `chmodSync` after), atomically `renameSync` over the original, then evict the path from the read cache so no stale pre-scrub view survives. Files with nothing to remove are never touched (`if (!changed) continue`). Filter replacements (boundary sentinels) are serialized back as real lines.
**Invariant:** readers never observe a half-rewritten shard (rename is atomic); the scrubber never deletes evidence it cannot understand; scrubbed bytes carry 0600 permissions even if umask would loosen them.
**Probe:** `src/main/activity-event-file.test.ts:175-196` ("atomically scrubs protected-app records while retaining ordinary and malformed evidence": 1 removed, output still contains `"ordinary"` AND the literal junk line `"malformed-but-preserved"`, contains no `"private"`). Runner note: suite blocked by missing `node_modules`; verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "scrub protected activity events temporary rename", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt temp+chmod+rename rewriting and verbatim preservation of unparsable lines for any retroactive-redaction pass over logs; adapt the pid suffix to your concurrency marker; omit Electron data-directory ownership specifics. Coverage checked: `no_recorded_issue`.

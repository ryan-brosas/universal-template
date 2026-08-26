<!-- capsule-v2 -->
# Recordings library CLI — how does an agent enumerate, pick, and re-open past recordings when directory names are user-supplied and entries can vanish mid-scan?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What makes a recordings library safe to list and resolve from a CLI when the directory tree is concurrent and its names are untrusted?

## Evidence-gated listing + containment-guarded active marker + one-component names
**Path/Symbol:** `skills/cdp/sdk/recording.ts:listRecordings` (:132-149), `latestRecording` (:151-153), `activeRecording` containment guard (:119-130), `safeName` (:180-189), `setAutoRecording` atomic persist (:106-117), `runRecordingsCli` (:474-501).
**Signature:** `listRecordings(): Promise<string[]>` · `latestRecording(): Promise<string | undefined>` · `runRecordingsCli(args: string[]): Promise<number>` (module-run gated by `import.meta.url === pathToFileURL(argv[1]).href`, :503-508).
**Data Shape:** newest-first paths; a recording dir counts only if it holds `meta.json` OR `events.jsonl`; sort key is the EVIDENCE mtime (`events.jsonl`) falling back to the dir's own mtime.

### Decisive source
```ts
await Promise.all(names.filter(name => !name.startsWith('.')).map(async name => {
  if (!(await stat(path)).isDirectory()) return;
  const evidence = join(path, 'events.jsonl');
  const modified = await stat(existsSync(evidence) ? evidence : path);
  if (existsSync(join(path, 'meta.json')) || existsSync(evidence)) {
    found.push({ path, modified: modified.mtimeMs });   // per-entry try/catch: concurrent deletion tolerated
  }
}));
return found.sort((a, b) => b.modified - a.modified).map(item => item.path);

// activeRecording: the on-disk marker is containment-checked before use
const child = relative(root, candidate);
if (child === '..' || child.startsWith('..' + sep) || isAbsolute(child)) return undefined;

// setAutoRecording: preference persists via tmp+rename so readers never see a torn config
const temporary = `${target}.${process.pid}.tmp`;
await writeFile(temporary, JSON.stringify({ enabled }) + '\n', { mode: 0o600 });
await rename(temporary, target);
```

**Flow:** `recordings --latest` prints `latestRecording()` or exits 1 ("no recordings found") → `recordings enable|disable` atomically flips `recording.json` (and disabling unlinks an AUTO recording's marker) → bare `recordings` prints a three-line status (`auto-recording: on/off (source)` from the CDP_RECORD > config > default ladder, plus `active:` and `latest:`) → anything else prints usage and exits 2. `latestRecording()` is just `listRecordings()[0]`, so every consumer shares one admission+sort definition of "newest".
**Invariant:** DIRECTORY CONTENT IS HOSTILE — dotfiles are skipped (they hold the port-scoped `.active-*` marker), non-directories are skipped, evidence files gate admission (an empty dir is invisible), per-entry stat failures degrade to omission instead of failing the whole scan, and sort order follows the EVIDENCE file because appending frames updates `events.jsonl` while the dir mtime stays behind. The active-recording marker read back from disk must be containment-checked against `recordingsRoot()` before any use — a tampered marker must never redirect writes outside the library. Names are normalized to ONE safe path component (`safeName` throws on separators/dots, collapses junk to `-`) with collision suffixing `-2`, `-3`… in `createRecording`.
**Probe:** deterministic source pins (this seam has no dedicated suite): `grep -n "export async function listRecordings\|export async function latestRecording\|async function runRecordingsCli" skills/cdp/sdk/recording.ts` → :132/:151/:474. Behavioral adjacency: `'recording preference is off by default and persists explicit consent'` (`video.test.ts` :85-104) executes the enable/disable persistence half end-to-end against a temp home. Suite executed GREEN at this pin (17/17, pass 5).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "runRecordingsCli listRecordings", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 5: runRecordingsCli @ recording.ts:474-501 (callees_total=12 incl. all six accessors); listRecordings @ :132-149.
```

## Verdict
Adopt evidence-gated listing, shared `[0]`-derived "latest", containment-checked markers, and tmp+rename preference writes for any agent-side artifact library; adapt the admission predicate (meta.json/events.jsonl) to your artifact schema; omit the port-scoped `.active-<port>` marker naming only if your daemon is strictly single-instance (multi-port coexistence is why it exists). Caveat: no direct unit test drives listing/sort/containment (recorded block — deterministic pins used), and `recording.ts` coverage is no_recorded_issue + metadata_match at gen-matching index.

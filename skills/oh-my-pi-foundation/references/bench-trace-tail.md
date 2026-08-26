<!-- capsule-v2 -->
# Bounded trace tail reads — serving huge transcript tails without loading whole files

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you serve the readable tail of a possibly multi-GB agent transcript through an HTTP API — capped, path-safe, and normalized across artifact formats?

## seek-to-size-minus-cap + partial-line drop + resolve-under-root containment
**Path/Symbol:** `packages/metaharness/src/server.ts` — `#trace` (630-704), `readTextTail` (729-742), `TRACE_READ_CAP_BYTES` (726).
**Signature:** `readTextTail(file: string, cap: number): string`; `#trace(jobName, traceName, tail: number, raw: boolean): Response`.
**Data Shape:** cap = 32MiB; default view window `tail=120` lines clamped to [1..2000]; locator forms: real path under the job dir (`<trial>/agent/omp.txt`), `result.dump/...md`, or synthetic `record:<lineNumber>` (JSONL line address). Normalized entries: `{kind: assistant|toolResult|notice|question|answer|reference|conversation, ...}`.

### Decisive source
```ts
/** Trace files can be runaway-huge; the viewer only shows a tail anyway. */
const TRACE_READ_CAP_BYTES = 32 * 1024 * 1024;

/** Last `cap` bytes of a file as text, dropping a leading partial line when truncated. */
function readTextTail(file: string, cap: number): string {
    const size = fs.statSync(file).size;
    if (size <= cap) return fs.readFileSync(file, "utf8");
    const fd = fs.openSync(file, "r");
    try {
        const buf = Buffer.allocUnsafe(cap);
        const read = fs.readSync(fd, buf, 0, cap, size - cap);   // seek to size-cap
        const text = buf.subarray(0, read).toString("utf8");
        const nl = text.indexOf("\n");
        return nl === -1 ? text : text.slice(nl + 1);            // drop torn first line
    } finally { fs.closeSync(fd); }
}
...
const file = path.resolve(jobDir, trace.tracePath);
if (!file.startsWith(`${path.resolve(jobDir)}${path.sep}`) || !fs.existsSync(file)) {
    return Response.json({ error: "trace not found" }, { status: 404 });
}
```

**Flow:** look up the stored trace row's adapter-owned locator → `record:` prefix ⇒ read exactly one JSONL line by number and shape it into question/answer/reference entries (raw mode returns the bare JSON line) → otherwise resolve under the job dir and CONTAIN (`resolve` + `startsWith(root+sep)` defeats `../` escape via a poisoned locator) → read at most the last 32MiB, dropping the leading partial line that the byte cut may have produced → `.txt` NDJSON transcripts parse line-by-line into assistant/toolResult/notice entries with tool-result bodies clipped at 1600 chars and only the last `tail` entries returned; everything else is one `conversation` entry; `?raw=1` bypasses normalization.
**Invariant:** memory bound is constant (cap), never file size; a byte-window cut MUST discard its first fragment line or downstream JSON.parse silently loses events; locator strings from the store are untrusted input — contain them under the job root before touching the filesystem; raw mode is an explicit opt-in escape hatch.
**Probe:** `packages/metaharness/test/manager.test.ts:225-232` pins the normalized `.txt` path end-to-end (`entries` kinds `[assistant, toolResult]`, tools list); `:310-323` pins both non-`.txt` variants (edit markdown ⇒ single conversation entry; snapcompact `record:` ⇒ question/answer/reference). The 32MiB window itself is source-read (needs a huge fixture).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "readTextTail TRACE_READ_CAP_BYTES tracePath record containment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any endpoint that serves logs/transcripts: fixed-byte tail window with torn-line drop, per-line normalization with body clipping, strict locator containment. Adapt cap size, entry shapes, and clipping lengths to your UI; omit nothing else — all three behaviors are failure modes porters hit in production.

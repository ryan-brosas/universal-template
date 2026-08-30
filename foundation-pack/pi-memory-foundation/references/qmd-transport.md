<!-- capsule-v2 -->
# qmd transport — CLI wrapper with Windows shim bypass, ANSI stripping, and collection setup

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent invoke the qmd CLI reliably across platforms — bypassing broken Windows cmd-shims, stripping ANSI noise from JSON output, and auto-creating the collection?

## qmd transport
**Path/Symbol:** `index.ts:isQmdCommand` (877–881), `resolveQmdJsPath` (894–911), `buildQmdSpawn` (918–928), `buildQmdEnv` (930–934), `execFileWithQmdOptions` (936–946), `stripAnsi` (1263–1269), `parseQmdJson` (1271–1289), `qmdInstallInstructions` (1014–1027), `qmdCollectionInstructions` (1029–1037), `setupQmdCollection` (1040–1072).
**Signature:** `resolveQmdJsPath(env?): string | null`; `buildQmdSpawn(file, args, platform?, qmdJsPath?): {file, args}`; `buildQmdEnv(env?): NodeJS.ProcessEnv`; `setupQmdCollection(): Promise<boolean>`.
**Data Shape:** `QMD_JS_REL = node_modules/@tobilu/qmd/dist/cli/qmd.js`. `execFileFn` is a swappable seam (`_setExecFileForTest`/`_resetExecFileForTest`). `stripAnsi` removes CSI (`\u001b[[0-9;?]*[ -/]*[@-~]`) and OSC (`\u001b\][^\u0007]*(\u0007|\u001b\\)`) sequences.

### Decisive source
```ts
// buildQmdSpawn (918-928): on win32, invoke qmd's JS entry with node directly
if (platform !== "win32" || !isQmdCommand(file) || !qmdJsPath) return { file, args: [...args] };
return { file: "node", args: [qmdJsPath, ...args] };

// buildQmdEnv (930-934): force NO_COLOR so JSON stays parseable
const qmdEnv = { ...env, NO_COLOR: "1" }; delete qmdEnv.FORCE_COLOR; return qmdEnv;

// parseQmdJson (1271-1289): find the first line starting with [ or { and parse from there
const cleaned = stripAnsi(stdout);
const lines = cleaned.split(/\r?\n/);
const startLine = lines.findIndex(l => { const s = l.trimStart(); return s.startsWith("[") || s.startsWith("{"); });
if (startLine === -1) throw new Error(`Failed to parse qmd output: ${trimmed.slice(0, 200)}`);
return JSON.parse(lines.slice(startLine).join("\n").trim());
```

**Flow:** (1) `resolveQmdJsPath` scans PATH entries for a sibling `node_modules/@tobilu/qmd/dist/cli/qmd.js` and caches the result. (2) On win32, `buildQmdSpawn` rewrites the command to `node <qmdJsPath> …` to bypass the broken `.cmd`/`.ps1` shims; `buildQmdEnv` forces `NO_COLOR=1`. (3) `parseQmdJson` strips ANSI and extracts the JSON payload from the first `[`/`{` line. (4) `setupQmdCollection` runs `qmd collection add` + `qmd context add` best-effort and seeds the status cache.

**Invariant:** qmd JSON output is parsed after ANSI stripping and payload-locating, so spinners/progress bars never break parsing; on Windows the shims are bypassed by invoking qmd's JS entry with node; collection setup is idempotent and best-effort.

**Probe:** `test/unit.test.ts` — `buildQmdSpawn` describe (:270), `resolveQmdJsPath` describe (:315), `qmdInstallInstructions`/`qmdCollectionInstructions` describes (:629/:641); `runQmdSearch qmd diagnostics` describe (:1189): `strips qmd spinner control sequences from stderr failures` (:1194), `strips qmd spinner control sequences from the fallback error message` (:1207), `removes FORCE_COLOR and sets NO_COLOR for qmd child processes` (:1245). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "resolveQmdJsPath buildQmdSpawn buildQmdEnv parseQmdJson stripAnsi setupQmdCollection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Windows shim bypass via `resolveQmdJsPath`, the `NO_COLOR` env forcing, the ANSI-stripping JSON parser, the swappable `execFileFn` test seam, and the idempotent collection setup. Adapt the qmd package path, collection name, and timeout values to the host. Omit the qmd vendor's own behavior unless a target needs it.

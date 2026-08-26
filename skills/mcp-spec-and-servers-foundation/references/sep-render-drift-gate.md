<!-- capsule-v2 -->
# SEP render drift gate — how do I regenerate published pages from hand-written sources and compare them like-for-like when a formatter owns the committed bytes?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** My committed docs are generator output AFTER Prettier — how does --check avoid false positives while still catching real drift, and how are proposal metadata and navigation kept idempotent?

## Format-normalized regenerate-and-compare over convention-parsed sources
**Path/Symbol:** `scripts/render-seps.ts:parseSEPMetadata` (42–85), `generateSEPPage` (139–175), `updateDocsJson` (307–356), `main` check branch (397–441).
**Signature:** `function parseSEPMetadata(content: string, filename: string): SEPMetadata | null`; `async function main()` with `--check`.
**Data Shape:** sources `seps/<number>-<slug>.md` (grammar `^(\d+)-(.+)\.md$`); outputs `docs/seps/index.mdx`, one `docs/seps/<number>-<slug>.mdx` per SEP, and rewritten `docs/docs.json` nav; check mode collects {path, expectedContent} then compares formatted copies.

### Decisive source
```ts
// skip-list BEFORE grammar; non-conforming names warn-and-skip:
if (filename === "TEMPLATE.md" || filename === "README.md" || filename.startsWith("0000-")) return null;
const filenameMatch = filename.match(/^(\d+)-(.+)\.md$/);
if (!filenameMatch) { console.warn(`Warning: Skipping ${filename} …`); return null; }
// --check: format regenerated .mdx in a temp dir BEFORE byte-compare:
execFileSync(npx, ["prettier", "--write", ...mdxTempFiles], { stdio: "pipe" });
if (!fs.existsSync(original)) { console.error(`Missing file: ${original}`); hasChanges = true; }
else if (existing !== formatted) console.error(`File out of date: ${original}`);
```

**Flow:** read all SEP markdown → parse metadata by convention (title from `^#\s+SEP-\d+:`; status/type/created/accepted/authors/sponsor/PR via bullet regexes; PR falls back to SEP number) → generate per-page MDX (body sliced from `## Abstract`; FINAL pages get the point-in-time historical-record notice; status→badge-color map: final green, accepted blue, in-review yellow, draft gray, rejected/withdrawn red, dormant orange, superseded purple) + index table sorted newest-first + status-grouped nav → **updateDocsJson is an idempotent tab upsert**: replace an existing SEPs tab or insert before Community, and strip the legacy SEPs group from Community → write mode emits files then Prettier-formats them; check mode regenerates into a mkdtemp dir, formats the COPIES, byte-compares against committed, lists missing/out-of-date files, exits 1 naming `npm run generate:seps`.
**Invariant:** comparison happens on FORMATTED output because committed bytes are formatted output of the same generator — normalize both sides before comparing, else formatter drift false-positives forever; unknown/malformed inputs degrade to warn-and-skip, never crash the batch.
**Probe:** `npm run check:seps` at HEAD ⇒ "Found 41 SEP(s) … All SEP documentation is up to date." RED twin: append one newline to `docs/seps/index.mdx` ⇒ "File out of date: …/docs/seps/index.mdx" + fix-command hint + exit 1 (both observed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "parseSEPMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt format-normalized drift gates for generated docs and convention-based source parsing with skip-lists ordered BEFORE grammar checks. Adapt badge/status vocabularies, the nav upsert target, and Prettier to your stack (the invariant is normalize-before-compare, not any specific formatter). Omit Mintlify JSX components and MCP's SEP lifecycle politics. Coverage: no_recorded_issue/metadata_match in the FULL graph (best-effort caveat); no dedicated unit test — npm gate is the probe.

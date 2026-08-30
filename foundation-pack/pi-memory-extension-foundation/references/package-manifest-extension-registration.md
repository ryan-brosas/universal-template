<!-- capsule-v2 -->
# Package manifest registration — how does a single-file extension get discovered, shipped, and installed?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839` (`package.json`, `README.md`); Codebase Memory `pi-memory-extension`. **Question:** A porter must know the minimum manifest contract a coding-agent host needs to discover and load one TypeScript file as an extension — and which dependencies the manifest is silent about.

## Discovery + shipping plane (`package.json`)
**Path/Symbol:** `package.json:25–29` (`pi.extensions`), `:30–35` (`files` allowlist), `:22–24` (`engines`).
**Signature:** n/a — declarative JSON; the load-bearing key is `"pi": { "extensions": ["./pi-memory.ts"] }`.
**Data Shape:** name/version/description/keywords (`pi-package`, `pi-extension`) for registry routing; `files` ships EXACTLY `pi-memory.ts`, `docs/`, `README.md`, `LICENSE`; `engines.node >=20`.

### Decisive source
```json
"engines": { "node": ">=20" },
"pi": {
  "extensions": [
    "./pi-memory.ts"
  ]
},
"files": [
  "pi-memory.ts",
  "docs/",
  "README.md",
  "LICENSE"
]
```

**Flow:** host install channel (README :15–23: `pi install npm:pi-memory-extension`, or git URL forms) → package read → `pi.extensions` array names entry files relative to package root → factory in each file invoked with ExtensionAPI.
**Invariant:** Discovery is an explicit path list, not convention scanning — renaming or moving `pi-memory.ts` without updating `pi.extensions` breaks loading while everything else still builds. The manifest declares NO `dependencies` field at all even though source imports `typebox` (:2): runtime typebox is HOST-PROVIDED (pass-4 probe: standalone `require.resolve('typebox')` ⇒ MODULE_NOT_FOUND). A porter extracting this file must either target a host that bundles typebox or add the dependency explicitly. Cosmetic doc gap recorded: README's global tree (:59–76) omits `index.md` although init creates it and design.md:120 lists it.
**Probe:** No upstream test runner exists. Pass-4 evidence: whole-file direct reads of `package.json` (36 lines) and `README.md` (108 lines); MCP `check_index_coverage` on all four repo files ⇒ `no_recorded_issue` (`metadata_match` on non-TS planes — JSON/doc surfaces are not symbol-indexed, so manifest facts are pinned by byte-reads only). Adversarial note: no graph retrieval can find this plane (JSON not token-indexed as symbols); treat manifest seams as filesystem-cited.
**Coverage caveat:** graph coverage for `package.json`/`README.md` is metadata-level; claims above cite exact line ranges from full reads at pin.

## Get live surrounding code
**Retrieve:** no symbol graph exists for JSON manifests — verify against the checkout:
```bash
git -C <checkout> show HEAD:package.json   # exact bytes at pin f3b4377f
```
(Executed pass 4 via direct read; HEAD verified `f3b4377f46d7…` before citing.)

## Verdict
Adopt an explicit extension-entry manifest key with a minimal `files` allowlist when building host-plugin systems — discovery should be data, not directory scanning. Adapt the key name/taxonomy to the host (`pi.extensions` here). Omit nothing silently: if your extension imports host-bundled libs, say so in docs or declare them — undeclared runtime deps are this manifest's one real trap. Coverage caveat: manifest/docs plane pinned by direct reads + executed resolution probe; no upstream suite.

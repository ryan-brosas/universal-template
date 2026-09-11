<!-- capsule-v2 -->
# Pi host compatibility gate — how do you warn when the host runtime is too old for your extension?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How does an extension detect WHICH Pi host it loaded into and whether that version supports required continuation APIs?

## Pi host compatibility gate
**Path/Symbol:** `src/host-compatibility.ts:compareVersions/detectPiHostVersion/piHostCompatibilityWarning` (:25–37, :39–72, :74–81).
**Signature:** `compareVersions(left, right): number | undefined` (undefined on unparseable input — never throws); `detectPiHostVersion(cliPath = process.argv[1]): string | undefined`; warning text names the exact broken capability.
**Data Shape:** `MINIMUM_PI_HOST_VERSION = "0.80.6"`; recognized host package names = {"@earendil-works/pi-coding-agent", "@mariozechner/pi-coding-agent"}.

### Decisive source
```ts
if (a.prerelease && !b.prerelease) return -1;      // 0.80.6-beta.1 < 0.80.6
...
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
if (typeof manifest.name === "string" &&
    PI_HOST_PACKAGE_NAMES.has(manifest.name) && ...
// walk UP from realpath(cliPath) until a package.json names a known Pi host
```

**Flow:** realpath the running CLI → walk parent directories reading each package.json until one matches a known host package name and carries a string version → numeric triple compare against the floor; prerelease sorts BELOW any release of the same triple; below-floor yields a warning that says WHY it matters ("Actor triggerTurn and other host continuations may be ignored").
**Invariant:** Detection must survive symlinks (realpathSync BEFORE walking — argv[1] may point through bin links); unreadable manifests are skipped silently but the walk continues to the filesystem root (`parent === directory` sentinel); unparseable versions return undefined so callers treat them as "cannot judge" rather than "too old"; no match ⇒ no warning (foreign hosts stay quiet).
**Probe:** `tests/host-compatibility.test.ts` ("compares release and prerelease versions" pins 0.80.5<floor, 0.80.6==0, 0.80.10>floor, 0.80.6-beta.1<floor); grep -c 'localeCompare(b.prerelease' src/host-compatibility.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "compareVersions detectPiHostVersion piHostCompatibilityWarning minimum host version", limit: 10 });
// detectPiHostVersion Function src/host-compatibility.ts 39-72
```

## Verdict
Adopt the realpath-then-walk package detection + capability-naming warning pattern for any extension with host-version-sensitive behavior; adapt package-name set and floor; omit prerelease handling only if your hosts never ship betas.

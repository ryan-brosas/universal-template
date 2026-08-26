<!-- capsule-v2 -->
# SPDX-stub SBOM + hash.txt integrity plane — what does this distribution actually promise about its own integrity?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** Which self-identity/integrity artifacts does a packaged .NET product ship, and how hollow may they legally be?

## Per-packaging-root stub SBOM twins + one-line sha256
**Path/Symbol:** `manifest.spdx.json` (root, 46 lines) and `NetCore/manifest.spdx.json` (byte-twin); `hash.txt` (single line, 66 bytes).
**Signature:** SPDX-2.2 document: `files: []`, one package `Microsoft.VisualStudio.SolutionPersistence 1.0.0` with `packageVerificationCodeValue: "da39a3ee5e6b4b0d3255bfef95601890afd80709"` (sha1 of EMPTY content), `filesAnalyzed: true`, all license fields `NOASSERTION`; creator `"Tool: Microsoft.SBOMTool-0.2.7"`.
**Data Shape:** the two twins differ in exactly two fields — the `documentNamespace` tail token (`…umJ7z5xl30-uInbhp6Ibhw` vs `…ZMpo5mmSY0eXz_4xmn6QeQ`) and the `created` timestamp (18:59:07Z vs 18:59:10Z, +3 s); everything else byte-equal.

### Decisive source
```json
{
  "files": [],
  "packages": [ { "name": "Microsoft.VisualStudio.SolutionPersistence",
    "SPDXID": "SPDXRef-RootPackage",
    "packageVerificationCode": { "packageVerificationCodeValue":
      "da39a3ee5e6b4b0d3255bfef95601890afd80709" },
    "filesAnalyzed": true, "versionInfo": "1.0.0", "hasFiles": [] } ],
  "spdxVersion": "SPDX-2.2",
  "creationInfo": { "creators": ["Organization: Microsoft", "Tool: Microsoft.SBOMTool-0.2.7"] }
}
```
```
hash.txt → 41e6f64786e9722be5cbd7c734c242fa86d8771173b067f373795844bf6eef11
```

**Flow:** packaging tool emits one SBOM per packaging root (install root, NetCore/) → namespace uniqueness comes from a per-emission tail token, so twins never collide as SPDX documents even with identical content → `hash.txt` is the only whole-distribution self-hash and is what an external ledger can pin when no VCS exists.
**Invariant:** an SBOM's presence is NOT an integrity claim — empty `files[]` plus the empty-content verification code means the tool ran but attested nothing; consumers must treat these as compliance placeholders, not tamper evidence. The only real pin surface is hash.txt.
**Probe:** deterministic content assertions executed on shipped artifacts: `cmp` proves the twin delta is exactly lines 35+37 (namespace tail + created timestamp); `hash.txt` read back as one 64-hex-char line (both recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
// Honest negative result (executed live): the graph has NO node vocabulary for the SBOM plane —
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "spdx manifest package verification hash", limit: 8 });
// → total: 0. JSON artifacts are not indexed here; ground this seam by direct file reads only.
```

## Verdict
Adopt the shape: emit per-packaging-root SPDX documents with unique namespaces, plus a single-file distribution self-hash for environments without VCS identity. Adapt the creator/tool strings to your pipeline. Omit any expectation that such stubs verify anything — if you need real integrity, hash the payload yourself (as hash.txt does) and treat the SBOM as metadata compliance only.

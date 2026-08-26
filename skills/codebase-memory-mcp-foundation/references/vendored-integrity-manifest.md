<!-- capsule-v2 -->
# Vendored integrity manifest — how do you ship third-party code and PROVE it wasn't tampered with at build/test time?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does a fail-closed checksum manifest test look like?

## Relocatable checksum list + zero-entries structural failure
**Path/Symbol:** `tests/test_security.c:vendored_integrity_manifest_is_relocatable_and_fail_closed` (67–100) + `scripts/vendored-checksums.txt` + `scripts/security-vendored.sh`.
**Signature:** Test asserts over the manifest format: `<64-hex> <path>` lines, paths confined to `vendored/` or `internal/cbm/vendored/`.
**Data Shape:** Script invariants pinned by exact-string greps: `MISSING=$((MISSING + 1))\n        CONTENT_DRIFT=1` (missing file ⇒ drift flag) and the BLOCKED branch when `CHECKED -eq 0` (manifest verified zero files ⇒ structural fail).

### Decisive source
```c
ASSERT(strncmp(path, "vendored/", strlen("vendored/")) == 0 ||
       strncmp(path, "internal/cbm/vendored/", strlen("internal/cbm/vendored/")) == 0);
ASSERT(entries > 0U);
...
ASSERT_NOT_NULL(strstr(script,
   "if [[ $CHECKED -eq 0 ]]; then\n    echo \"BLOCKED: checksum manifest verified zero "
   "files\"\n    STRUCTURAL_FAIL=1"));
```

**Flow:** CI computes sha256 per vendored path → test re-parses the manifest asserting every hash is 64-hex, every path inside the vendored roots, entry count > 0 → greps the verifying script for its fail-closed branches → any unmanifested source or content drift fails the security suite.
**Invariant:** A manifest that verifies ZERO files must be a hard failure — otherwise an emptying bug silently disables the whole check; relocation-safe means no absolute prefixes.
**Probe:** `tests/test_security.c:vendored_integrity_manifest_is_relocatable_and_fail_closed`, `vendored_integrity_rejects_unmanifested_source`, `vendored_integrity_update_refuses_dangerous_source_without_manifest_mutation`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "vendored_integrity", limit: 5 });
```

## Verdict
Adopt manifest-format assertions + zero-entry structural guard for supply-chain checks on vendored deps; adapt root prefixes; omit the CRLF normalization if your repo forbids them anyway.

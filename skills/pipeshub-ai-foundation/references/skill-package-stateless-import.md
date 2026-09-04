<!-- capsule-v2 -->
# Stateless skill package import — how do you import npm/URL/upload skill packs with NO server-side staging state?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How does a preview→confirm import flow work when the server refuses to keep ANY staging state between the two calls — and what are the archive-safety rules?

## Pure fetch-and-parse preview; the CLIENT round-trips the bytes on confirm
**Path/Symbol:** `backend/python/app/services/skills/package_importer.py:SkillPackageImporter.preview_npm/preview_url/preview_upload/_files_to_preview/_strip_common_prefix/_reject_unsafe_path/_extract_by_hint` (L37–279).
**Signature:** `preview_npm(spec: PackageSpec) -> ImportPreview` / `preview_url(url) -> ImportPreview` (async) · `preview_upload(filename, data) -> ImportPreview` (sync); `_files_to_preview(files: dict[str,bytes], *, source_label) -> ImportPreview`.
**Data Shape:** `ImportPreview{name, description, version, content, resources: dict[rel-path→text], warnings[], skipped_binary_resources[], source_label}` — content is the RAW SKILL.md text; resources restricted to top-level dirs `scripts|references|assets`.

### Decisive source
```python
_MAX_ARCHIVE_BYTES = 25 * 1024 * 1024   # "a skill pack is markdown + small scripts, not a model checkpoint"
_MAX_ARCHIVE_MEMBERS = 500

def _strip_common_prefix(paths):
    # npm tarballs nest under 'package/'; zips under '<repo>-<sha>/'. Strip exactly
    # ONE shared leading segment only if EVERY entry shares it — flat archives untouched.
    segments = {p.split("/", 1)[0] for p in paths if "/" in p}
    if len(segments) == 1 and all(p.startswith(next(iter(segments)) + "/") for p in paths):
        return next(iter(segments)) + "/"
    return ""

def _reject_unsafe_path(path):   # zip-slip guard BEFORE a byte is kept
    if path.startswith(("/", "\\")) or re.search(r"(^|/)\.\.(/|$)", path):
        raise PackageImportError(f"Archive contains an unsafe path: {path!r}")

# Nested SKILL.md ('my-skill/SKILL.md') ⇒ resource paths strip that SAME prefix so
# 'scripts/foo.sh' resolves relative to SKILL.md, not archive root.
# Binary resources: decode-fail → skipped WITH warning (graph doc is a string field,
# not a blob store — Phase-3 blob offload belongs to the Node.js gateway).
```
The deliberate no-staging trade (module docstring): every `preview_*` is pure fetch-and-parse writing nothing to the graph; the REST layer shows the preview and a SEPARATE source-agnostic `finalize()` fed the exact `content`/`resources` the preview returned does `SkillManager.create()` + `write_resource()`. Avoiding staging tables/TTL caches (which would need sticky sessions or Redis across replicas) costs the client round-tripping KB-sized text it already received — documented so it isn't "rediscovered as a bug later".

**Flow:** npm: registry metadata → tarball URL → ≤25MB check → extract tar (≤500 members, zip-slip guard per member) → common-prefix strip → locate SKILL.md (root or nested) → parse+validate via the shared agent_loop_lib loader (`parse_skill_md` + `SkillValidator`) → collect text resources under the skill dir's three allowed kinds, skip binaries with warning → fold validator lints into `warnings`. URL/upload: same tail after `_extract_by_hint` picks zip-vs-tar by extension/content-type, falling back to MAGIC BYTES (`PK\x03\x04`) then try-tar-catch-zip.
**Invariant:** (1) No SKILL.md anywhere in the archive is a hard error naming the agentskills.io spec. (2) Zip-slip rejection happens during extraction, before anything is retained. (3) Ambiguous archives sniff bytes rather than trusting names. (4) All failures raise `PackageImportError(ValueError)` whose `str()` is always safe to show the user — internal detail leaks impossible by construction. (5) Binary skipping is a WARNING listing up to 5 files, never silent.
**Probe:** `tests/unit/services/skills/test_package_importer.py` (272L): zip with SKILL.md only :52; bundled_resources :63; common_prefix_is_stripped :74; binary_resource_skipped_with_warning :84; ignores_files_outside_resource_kinds :95; missing_skill_md_raises :104; non_utf8_skill_md_raises :128; **zip_slip_absolute_path_rejected** :134; too_large_upload_rejected :144; tar_gz_upload :150; content_sniff_when_no_extension_hint :156; npm 404→not_found :191; missing_tarball :202; oversized_tarball :224.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "SkillPackageImporter _files_to_preview _strip_common_prefix _extract_by_hint" --detail ids
```

## Verdict
Adopt the stateless preview/confirm split (client round-trips content), single-common-segment stripping, extraction-time zip-slip guard, magic-byte format sniffing, binary-skip-with-warning, and the always-user-safe error type. Adapt size caps and resource-kind list to the host. Omit the Node.js blob-offload half.

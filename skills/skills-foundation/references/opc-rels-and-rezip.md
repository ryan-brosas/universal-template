<!-- capsule-v2 -->
# OPC Relationship Resolver + Safe Rezip — how does a relationship target become a package part name, and why is [Content_Types].xml stored uncompressed first?

**Source:** anthropics/skills (office/helpers, vendored identically in pptx/docx/xlsx skills; source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What are the exact resolution rules for `Relationship` targets against an unpacked OOXML tree, and what does the repack step guarantee?

## opc_target path algebra + rezip contract
**Path/Symbol:** `skills/docx/scripts/office/helpers/__init__.py:24–55` (`opc_target`; byte-identical twins at `skills/pptx/scripts/office/helpers/__init__.py:24–55`, `skills/xlsx/...` — md5 f8e903c1b8fb9afd8ff0fc3a20ee2a2f ×3); `rels_source_part` :57–59; `part_text` :62 (`utf-8 surrogateescape`); `safe_extract` :73–81; `rezip` :84–105.
**Signature:** `opc_target(target: str, source_part: str, target_mode: str = "") -> str | None`; `rezip(src_dir: Path, out_path: Path) -> None`.
**Data Shape:** returns canonical absolute part name (`"ppt/slides/slide1.xml"` style, `/`-joined, no leading slash) or None for non-parts. Raises on backslash targets, package-escaping `..`, and empty resolutions.

### Decisive source
```python
if target_mode.lower() == "external":
    return None
if _SCHEME_RE.match(target):          # http(s):, mailto:, ... never parts
    return None
...
joined = posixpath.join(posixpath.dirname(source_part), target)
for segment in posixpath.normpath(joined).split("/"):
    if segment == "..":
        if not parts:
            raise ValueError(f"relationship target escapes the package: {target!r}")
        parts.pop()
```
```python
zf.write(ct, ct.relative_to(src_dir), compress_type=zipfile.ZIP_STORED)
```

**Flow:** external mode or scheme-bearing → None (not a part) → percent-decode → reject `\` → absolute `/target` joins from root else relative to `dirname(source_part)` → normpath walk where `..` pops or RAISES at root → join with `/`. Repack side: `[Content_Types].xml` written FIRST as ZIP_STORED, everything else deflated, deterministic sorted order, mkstemp+os.replace atomic swap preserving prior file mode.
**Invariant:** The leading-slash rule is OPC law — relative targets resolve against the SOURCE PART's directory, not the package root, which is exactly where naive string handling goes wrong. `..` escaping the root is malformed input, not a resolvable path. Content_Types-first-uncompressed mirrors what Office writers do so picky consumers see it immediately.
**Probe:** No unit tests upstream. Deterministic probes: call `opc_target("../slides/slide2.xml", "ppt/slideLayouts/_rels")`-shaped inputs and verify join/reject semantics; md5-verified the three vendored copies identical so any twin may be cited.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "opc_target", limit: 5 });
```

## Verdict
Adopt verbatim for any OOXML rels traversal, link rewriting, or part-graph analysis. Adapt error strings to your harness. Omit nothing — this ~80-line module is the shared substrate of all three document skills. Caveat: no direct tests; pinned by whole-file read + graph triple-hit.

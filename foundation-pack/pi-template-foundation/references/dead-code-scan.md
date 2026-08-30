<!-- capsule-v2 -->
# Template dead-code scan — what does "dead code" mean in a repository whose product is configuration and membership is data?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** How do you define and detect dead weight when there is no import graph — only scripts, catalogs, and markdown?

## Reference-text scan + catalog-membership scan with drain-managed exemptions
**Path/Symbol:** `scripts/dead-code.py` (module-level scan; unused-script error line 34; membership block lines 44–58, exemption lines 51–52).
**Signature:** module-level; concatenates every `.yml/.yaml/.md/.py/.toml/.cfg` file (skip dirs `.git node_modules .venv .veda .pi/fabric inspect`) into one text blob.
**Data Shape:** `known = union(packs.packs[].members[], manifest.retained[].name, manifest.removed[].name)`.

### Decisive source
```python
# 2. Skill files not in packs.json or manifest
...
for root, dirs, files in os.walk(skills_dir):
    if "SKILL.md" in files:
        name = os.path.basename(root)
        # skip pack routers (pack-* dirs) and foundation leaves (managed by drain)
        if name.startswith("pack-") or name.endswith("-foundation"):
            continue
        if name not in known:
            errors.append(f"skill not in packs.json/manifest: {name}")
```
Script half of the gate: a `scripts/*.py` file is DEAD when its filename never appears in the concatenated repo text (`if f not in all_text`) — reference-by-mention is the contract for a no-import repository.

**Flow:** build reference blob → flag unreferenced `scripts/*.py` (except `__init__.py`) → load `packs.json` + `manifest.json`, union member/retained/removed names into `known` → walk `.pi/skills` for SKILL.md dirs, EXEMPTING `pack-*` routers and `*-foundation` leaves (both are managed by automated drain lanes, not hand-catalogued) → error on any remaining unlisted skill → exit 0/1.
**Invariant:** "dead" is defined RELATIVE TO THE MEMBERSHIP DATA, not to call graphs; managed namespaces are exempted explicitly so automation lanes never fight the gate. Note the asymmetry: `manifest.removed[]` names count as KNOWN — removal is recorded history, not an error.

**Probe:** `python3 scripts/dead-code.py` executed live at the pin → stdout `DEAD CODE OK`, exit 0 (observed 2026-08-25; the full-tree text walk is slow at this repo's current size — budget minutes, not seconds). CI wiring via check.yml step "Dead code".

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "dead code unused script unlisted skill foundation skip", limit: 5 });
// -> weak symbol hits only: dead-code.py is MODULE-LEVEL code with no Function graph nodes; discovery used file-level query + direct read (honest retrieval caveat).
```

## Verdict
Adopt "dead = unreferenced by any config/doc text" plus data-driven membership sets with explicit managed-namespace exemptions. Adapt the extension list of the reference blob to your repo's doc formats. Omit nothing else — the whole gate is ~60 lines and stdlib-only.

<!-- capsule-v2 -->
# Catalog integrity gate — how do you mechanically prove a progressive-disclosure skill catalog has no drift between membership JSON, ledger, router listings, and disk?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** What exact set comparisons make catalog drift impossible to miss, and how do you scan a living state file without failing on its history?

## Three-way parity over packs.json, manifest.json, and router bullets
**Path/Symbol:** `scripts/check-integrity.py` (module-level gate; helper `skill_dir` lines 19–24; router-parity block lines 49–67).
**Signature:** `def skill_dir(name):` (untyped at pin; returns a directory path or `None`) — walks `.pi/skills` once, returns the first dir whose basename matches and which contains `SKILL.md`.
**Data Shape:** consumes `.pi/skills/packs.json` (`packs[].{id,members[]}`) and `.pi/skills/manifest.json` (`retained[].name`); emits one error string per drift; exit 0/1.

### Decisive source
```python
# 4. router parity (pack router lists exactly the packs.json members)
for pack in packs.get("packs", []):
    pid = pack["id"]
    router = os.path.join(SKILLS, pid, "SKILL.md")
    ...
    router_members = set()
    for line in rt.splitlines():
        line = line.strip()
        if line.startswith("- ") and not line.startswith("##"):
            name = line[2:].split(":")[0].strip()
            if name and not name.startswith("#"):
                router_members.add(name)
    catalog_members = set(pack.get("members", []))
    if catalog_members != router_members:
        errors.append(
            f"router mismatch {pid}: catalog-only={sorted(catalog_members-router_members)} "
            f"router-only={sorted(router_members-catalog_members)}"
        )
```

**Flow:** validate both JSON files parse → every `packs.json` member resolves to an on-disk dir under `<packId>/<member>` → every manifest `retained` name resolves via `skill_dir` → per pack, parse the router's bullet list into a name set and require set EQUALITY with the catalog members, reporting both directions of the diff → scan live config for references to deleted machinery.
**Invariant:** membership has exactly ONE owner (`packs.json`); routers and manifests are projections that must re-derive to it byte-for-byte in name-set form. A leaf added to disk alone fails; a router line dropped fails with the precise missing name.

The second decisive trick — scanning a state file that embeds history:
```python
live_state_lines = []
for line in st.splitlines():
    # skip changelog rows (start with a date like "| 2026-")
    if line.strip().startswith("| 2026-"):
        continue
    live_state_lines.append(line)
```
**Invariant:** only the LIVE section of `.pi/state.md` may fail the dangling-reference check (deleted `scripts/*.mjs`, `canonical-check`); dated changelog table rows are historical record and are exempt.

**Probe:** `python3 scripts/check-integrity.py` executed live at the pin → stdout `OK: 6 packs, all consistent`, exit 0 (observed 2026-08-25). CI wiring: `.github/workflows/check.yml` step "Structural integrity" tees output to an artifact uploaded only on failure.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "router parity packs members mismatch structural integrity", limit: 5 });
// -> pi-template.scripts.check-integrity.skill_dir Function scripts/check-integrity.py 19-24
```

## Verdict
Adopt the single-owner membership model with set-equality projections and the two-directional drift message; adopt the dated-row changelog exemption for any state file that accumulates history. Adapt the bullet-parsing heuristic (`"- name:"` prefix) to your router's actual list syntax. Omit Pi-specific path layout; keep the check stdlib-only and dependency-free.

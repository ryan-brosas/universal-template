#!/usr/bin/env python3
"""foundation-validator.py — lightweight structural gate for foundation-pack/.

Validates *-foundation leaves that ship a SKILL.md. Historical leaves without
frontmatter stay grandfathered. Machine-local provenance paths warn only.

Exit 1 on P0 structural defects. Zero dependencies.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PACK = BASE / "foundation-pack"

MACHINE_LOCAL = re.compile(r"/mnt/|/home/[^/]+/inspo|\.skill-mining-work/", re.I)
UNPROMOTED_NOTES = re.compile(r"internal working notes|no upstream VCS", re.I)
CITED_REF = re.compile(r"`references/([^`]+)`")


def _cited_refs(text: str) -> list[str]:
    out: list[str] = []
    for cited in CITED_REF.findall(text):
        if any(ch in cited for ch in "<>*'"):
            continue  # template placeholders or malformed citations
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md", cited):
            continue
        out.append(cited)
    return out


def _parse_fm(text: str):
    spec = importlib.util.spec_from_file_location(
        "catalog_quality", str(Path(__file__).with_name("catalog-quality.py")))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_frontmatter(text)


def validate_pack(base: Path = PACK) -> tuple[list[str], list[str]]:
    p0: list[str] = []
    warns: list[str] = []
    if not base.is_dir():
        return p0, warns
    for d in sorted(base.iterdir()):
        if not d.is_dir() or not d.name.endswith("-foundation"):
            continue
        skill = d / "SKILL.md"
        if not skill.is_file():
            p0.append(f"{d.relative_to(base.parent)}: missing SKILL.md")
            continue
        rel = skill.relative_to(base.parent)
        text = skill.read_text(encoding="utf-8", errors="replace")
        fm = _parse_fm(text)
        if not fm:
            p0.append(f"{rel}: frontmatter missing or unparseable")
            continue
        if not fm.get("name"):
            p0.append(f"{rel}: name missing")
        elif fm.get("name") != d.name:
            p0.append(f"{rel}: name {fm.get('name')!r} != directory {d.name!r}")
        if not str(fm.get("description", "")).strip():
            p0.append(f"{rel}: description missing")
        if UNPROMOTED_NOTES.search(text):
            p0.append(f"{rel}: internal working notes are not a promoted foundation")
        refs_dir = d / "references"
        disk = {f.name for f in refs_dir.glob("*.md")} if refs_dir.is_dir() else set()
        for cited in _cited_refs(text):
            if cited not in disk:
                p0.append(f"{rel}: cited references/{cited} missing on disk")
        if MACHINE_LOCAL.search(text):
            warns.append(f"{rel}: machine-local provenance path (prefer portable upstream id + commit)")
    return p0, warns


def selftest() -> int:
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        leaf = root / "demo-foundation"
        leaf.mkdir()
        (leaf / "SKILL.md").write_text(
            "---\nname: demo-foundation\ndescription: Use when testing.\n---\n# Demo\n",
            encoding="utf-8",
        )
        p0, _ = validate_pack(root)
        if p0:
            print(f"FAIL valid foundation should pass, got {p0}")
            ok = False
        else:
            print("PASS valid foundation structure")
        (leaf / "SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
        p0, _ = validate_pack(root)
        if not p0:
            print("FAIL broken frontmatter should fail")
            ok = False
        else:
            print("PASS broken frontmatter fails")
        empty = root / "empty-foundation"
        empty.mkdir()
        p0, _ = validate_pack(root)
        if not any("missing SKILL.md" in x for x in p0):
            print(f"FAIL missing SKILL.md should fail, got {p0}")
            ok = False
        else:
            print("PASS missing SKILL.md fails")
        (empty / "SKILL.md").write_text(
            "---\nname: wrong-name\ndescription: Use when testing.\n---\n# Wrong\n",
            encoding="utf-8",
        )
        p0, _ = validate_pack(root)
        if not any("!= directory" in x for x in p0):
            print(f"FAIL name mismatch should fail, got {p0}")
            ok = False
        else:
            print("PASS name mismatch fails")
        notes = root / "notes-foundation"
        notes.mkdir()
        (notes / "SKILL.md").write_text(
            "---\nname: notes-foundation\ndescription: Use when testing.\n---\n"
            "# Notes\n\n## Provenance\nUser-authored internal working notes; no upstream VCS.\n",
            encoding="utf-8",
        )
        p0, _ = validate_pack(root)
        if any("working notes" in error for error in p0):
            print("PASS internal working notes fail promotion")
        else:
            print(f"FAIL internal working notes should fail promotion, got {p0}")
            ok = False
    print("foundation-validator selftest: PASS" if ok else "foundation-validator selftest: FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    p0, warns = validate_pack()
    for w in warns[:20]:
        print(f"WARN  {w}")
    if len(warns) > 20:
        print(f"WARN  ... and {len(warns) - 20} more")
    for f in p0:
        print(f"FAIL  {f}")
    print(f"FOUNDATION VALIDATOR: {len(p0)} fail, {len(warns)} warn")
    return 1 if p0 else 0


if __name__ == "__main__":
    sys.exit(main())

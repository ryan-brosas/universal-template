#!/usr/bin/env python3
"""skill-catalog.py — deterministic discovery over skills and foundations.

Visible skills are deliberately few; hidden/cold skills and foundation-pack
leaves stay out of startup metadata and are found here:

    list / search / search-foundations / search-leverage / show / stats / generate

Metadata search only until a candidate earns a read. Classification (entry /
router / internal / cold / vendor) is owned by catalog-quality.py.
Zero dependencies.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
FOUNDATION_PACK = Path(os.environ.get("FOUNDATION_PACK", str(BASE / "foundation-pack")))
DOCS = BASE / "docs"
TOKEN_CHARS = 4
DESC_TRUNC = 160


def _load_catalog_quality():
    spec = importlib.util.spec_from_file_location(
        "catalog_quality", str(Path(__file__).with_name("catalog-quality.py")))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CQ = _load_catalog_quality()
parse_frontmatter = _CQ.parse_frontmatter
classify = _CQ.classify
CLASSES = ("entry", "router", "internal", "cold", "vendor")

STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "and", "or",
    "how", "does", "do", "is", "are", "our", "we", "my", "me", "use", "when",
    "find", "show", "skill", "skills", "have", "list", "what", "which",
}


def scan(*, skills_dir: Path | None = None) -> list[dict]:
    root = skills_dir or SKILLS
    local_dirs = _CQ.git_ignored_dirs(root)
    out: list[dict] = []
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        sm = d / "SKILL.md"
        if not sm.is_file():
            continue
        text = sm.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        hidden = str(fm.get("disable-model-invocation", "")).strip().lower() == "true"
        out.append({
            "name": fm.get("name", d.name),
            "folder": d.name,
            "desc": fm.get("description", ""),
            "hidden": hidden,
            "local": d.name in local_dirs,
            "cls": classify(d.name, hidden),
            "path": str(sm),
            "body": text,
            "body_low": text.lower()[:20000],
            "refs": sorted(p.name for p in (d / "references").glob("*.md"))
            if (d / "references").is_dir() else [],
        })
    return out


def scan_foundations(*, pack_dir: Path | None = None) -> list[dict]:
    """Frontmatter metadata only; foundation bodies are not indexed deeply."""
    root = pack_dir or FOUNDATION_PACK
    out: list[dict] = []
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not d.name.endswith("-foundation"):
            continue
        sm = d / "SKILL.md"
        if not sm.is_file():
            continue
        text = sm.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        stem = d.name[: -len("-foundation")] if d.name.endswith("-foundation") else d.name
        out.append({
            "name": fm.get("name", d.name),
            "stem": stem,
            "desc": fm.get("description", ""),
            "path": str(sm),
        })
    return out


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", query.lower())
            if t not in STOPWORDS and len(t) > 1]


def _normalize_query(query: str) -> str:
    q_low = re.sub(r"[^a-z0-9 ]", " ", query.lower()).strip()
    return " ".join(q_low.split())


def word_tokens(text: str) -> set[str]:
    """Whole-word tokens; avoids matching ``ui`` inside ``arduino``."""
    return {chunk for chunk in re.split(r"[^a-z0-9]+", text.lower()) if chunk}


def _phrase_in_text(phrase: str, text: str) -> bool:
    if not phrase or len(phrase) <= 3:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b"
    return re.search(pattern, text.lower()) is not None


def score_metadata(
    item: dict,
    toks: list[str],
    query_low: str,
    *,
    include_body: bool = False,
) -> tuple[float, list[str]]:
    s = 0.0
    why: list[str] = []
    name_low = item["name"].lower()
    desc_low = item["desc"].lower()
    stem_low = item.get("stem", "").lower()
    name_tokens = word_tokens(name_low)
    stem_tokens = word_tokens(stem_low) if stem_low else set()
    desc_tokens = word_tokens(desc_low)
    body_tokens = word_tokens(item.get("body_low", "")[:20000]) if include_body else set()
    if query_low and query_low == name_low:
        s += 12.0
        why.append("exact name")
    for t in toks:
        if t in name_tokens:
            s += 4.0
            why.append("name:" + t)
        if stem_tokens and t in stem_tokens:
            s += 3.5
            why.append("stem:" + t)
        if t in desc_tokens:
            s += 2.0
            why.append("desc:" + t)
        if include_body and t in body_tokens:
            s += 0.5
    if query_low and _phrase_in_text(query_low, desc_low):
        s += 5.0
        why.append("desc phrase")
    if query_low and _phrase_in_text(query_low, name_low):
        s += 6.0
        why.append("name phrase")
    seen: set[str] = set()
    why = [w for w in why if not (w in seen or seen.add(w))]
    return s, why


def score_skill(skill: dict, toks: list[str], query_low: str) -> tuple[float, list[str]]:
    return score_metadata(skill, toks, query_low, include_body=True)


def _rank(items: list[dict], query: str, limit: int, *, include_body: bool) -> list[dict]:
    toks = tokens(query)
    q_low = _normalize_query(query)
    scored = []
    for item in items:
        s, why = score_metadata(item, toks, q_low, include_body=include_body)
        if s > 0:
            row = {"score": s, "why": why, "name": item["name"], "desc": item["desc"], "path": item["path"]}
            if "cls" in item:
                row["cls"] = item["cls"]
                row["hidden"] = item["hidden"]
            if "stem" in item:
                row["stem"] = item["stem"]
            scored.append(row)
    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]


def search(skills: list[dict], query: str, limit: int) -> list[dict]:
    return _rank(skills, query, limit, include_body=True)


def search_foundations(foundations: list[dict], query: str, limit: int) -> list[dict]:
    return _rank(foundations, query, limit, include_body=False)


def related(skills: list[dict], name: str, limit: int = 8) -> list[str]:
    hits = []
    for sk in skills:
        if sk["name"] == name:
            continue
        if re.search(r"`" + re.escape(name) + r"`", sk["body"]):
            hits.append(sk["name"])
        if len(hits) >= limit:
            break
    return hits


def visible_chars(skills: list[dict]) -> int:
    return sum(len(s["name"]) + len(s["desc"]) for s in skills if not s["hidden"])


def stats(skills: list[dict]) -> dict:
    vis = [s for s in skills if not s["hidden"]]
    by_class: dict[str, int] = {}
    for s in skills:
        c = s["cls"] or "unclassified"
        by_class[c] = by_class.get(c, 0) + 1
    largest = sorted(vis, key=lambda s: -len(s["desc"]))[:10]
    chars = visible_chars(skills)
    return {
        "total": len(skills),
        "visible": len(vis),
        "hidden": len(skills) - len(vis),
        "visible_chars": chars,
        "visible_tokens_approx": chars // TOKEN_CHARS,
        "classes": by_class,
        "largest": [{"name": s["name"], "desc_chars": len(s["desc"])} for s in largest],
    }


def _clean(desc: str) -> str:
    return desc.replace("\u2014", "-")


def _md_row(s: dict) -> str:
    desc = _clean(s["desc"])
    if len(desc) > DESC_TRUNC:
        desc = desc[:DESC_TRUNC - 1].rstrip() + "..."
    desc = desc.replace("|", "\\|")
    vis = "hidden" if s["hidden"] else "visible"
    return f"| [`{s['name']}`](../skills/{s['folder']}/SKILL.md) | {s['cls'] or 'unclassified'} | {vis} | {desc} |"


def _align_md_table(rows: list[str]) -> list[str]:
    parts = [[c.strip() for c in r.split("|")[1:-1]] for r in rows]
    ncols = max(len(c) for c in parts)
    parts = [c + [""] * (ncols - len(c)) for c in parts]
    widths = [max(len(row[i]) for row in parts) for i in range(ncols)]
    out: list[str] = []
    for row in parts:
        is_sep = all(c == "" or re.fullmatch(r":?-+:?", c) for c in row)
        if is_sep:
            cells = [("-" * max(3, widths[i])) for i in range(ncols)]
            line = "| " + " | ".join(c.center(widths[i]) for i, c in enumerate(cells)) + " |"
        else:
            line = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(row)) + " |"
        out.append(line)
    return out


def build_skill_catalog_md(skills: list[dict]) -> str:
    lines = [
        "<!-- GENERATED by scripts/skill-catalog.py (generate). Do not edit by hand; rerun the script. -->",
        "",
        "# Skill Catalog",
        "",
        "Derived from `skills/*/SKILL.md` metadata. Discovery tools:",
        "`python3 scripts/skill-catalog.py search \"<topic>\"`,",
        "`python3 scripts/skill-catalog.py search-foundations \"<topic>\"`,",
        "`python3 scripts/skill-catalog.py search-leverage \"<topic>\"`.",
        "",
    ]
    st = stats(skills)
    lines.append(f"{st['total']} skills: {st['visible']} visible, {st['hidden']} hidden. "
                 f"Visible startup metadata: ~{st['visible_chars']} chars "
                 f"(~{st['visible_tokens_approx']} tokens).")
    lines.append("")
    sections = [
        ("Entry skills", "entry", "Direct user-facing capabilities; trigger on request."),
        ("Routers", "router", "Automatic dispatch points; visible on purpose."),
        ("Internal", "internal", "Invoked by other skills or system components; hidden from startup metadata."),
        ("Cold specialists", "cold", "Rare specialists; searchable here, not loaded every session."),
        ("Vendor-managed", "vendor", "Installed and updated by their vendor; visibility follows integration."),
    ]
    for title, key, blurb in sections:
        rows = [s for s in skills if s["cls"] == key]
        if not rows:
            continue
        table = ["| Skill | Class | Visible | Description |", "|---|---|---|---|"] + [_md_row(s) for s in rows]
        lines += [f"## {title}", "", blurb, ""] + _align_md_table(table) + [""]
    unclassified = [s["name"] for s in skills if s["cls"] is None]
    if unclassified:
        lines += ["## Unclassified", "",
                  "These lack a class (catalog-quality fails on unclassified visible skills): "
                  + ", ".join(f"`{n}`" for n in unclassified), ""]
    return "\n".join(lines)


def _print_skill_hits(hits: list[dict]) -> None:
    for h in hits:
        vis = "hidden" if h.get("hidden") else "visible"
        reason = ", ".join(h["why"][:4])
        cls = h.get("cls") or "unclassified"
        print(f"  {h['score']:6.1f}  {h['name']:40} {cls:9} {vis:7} {reason}")


def _print_foundation_hits(hits: list[dict]) -> None:
    for h in hits:
        reason = ", ".join(h["why"][:4])
        print(f"  {h['score']:6.1f}  {h['name']:40} {reason}")


def cmd_list(skills: list[dict], args) -> int:
    rows = skills
    if args.visible:
        rows = [s for s in rows if not s["hidden"]]
    if args.hidden:
        rows = [s for s in rows if s["hidden"]]
    if args.klass:
        rows = [s for s in rows if s["cls"] == args.klass]
    if args.json:
        print(json.dumps([{k: s[k] for k in ("name", "cls", "hidden", "desc", "path")}
                          for s in rows], indent=2))
        return 0
    for s in rows:
        vis = "hidden" if s["hidden"] else "VISIBLE"
        local = " machine-local" if s.get("local") else ""
        print(f"{s['cls'] or 'unclassified':12} {vis:7} {s['name']}{local}")
    print(f"-- {len(rows)} skills", file=sys.stderr)
    return 0


def cmd_search(skills: list[dict], args) -> int:
    hits = search(skills, args.query, args.limit)
    if args.json:
        print(json.dumps(hits, indent=2))
        return 0
    if not hits:
        print(f"no skill matches for: {args.query!r}")
        return 0
    print(f"skill candidates for: {args.query!r}")
    _print_skill_hits(hits)
    print("Load only the candidate you need (skills/<name>/SKILL.md).")
    return 0


def cmd_search_foundations(foundations: list[dict], args) -> int:
    hits = search_foundations(foundations, args.query, args.limit)
    if args.json:
        print(json.dumps(hits, indent=2))
        return 0
    if not hits:
        print(f"no foundation matches for: {args.query!r}")
        return 0
    print(f"foundation candidates for: {args.query!r}")
    _print_foundation_hits(hits)
    print("Load only useful matches (foundation-pack/<name>/SKILL.md); then follow source pointers.")
    return 0


def cmd_search_leverage(skills: list[dict], foundations: list[dict], args) -> int:
    skill_hits = search(skills, args.query, args.limit)
    foundation_hits = search_foundations(foundations, args.query, args.limit)
    if args.json:
        print(json.dumps({"skills": skill_hits, "foundations": foundation_hits}, indent=2))
        return 0
    print(f"leverage candidates for: {args.query!r}")
    print("skills:")
    if skill_hits:
        _print_skill_hits(skill_hits)
    else:
        print("  (none)")
    print("foundations:")
    if foundation_hits:
        _print_foundation_hits(foundation_hits)
    else:
        print("  (none)")
    print("Search broadly; load narrowly. Read only candidates that materially help.")
    return 0


def cmd_show(skills: list[dict], args) -> int:
    sk = next((s for s in skills if s["name"] == args.name or s["folder"] == args.name), None)
    if sk is None:
        print(f"no such skill: {args.name}", file=sys.stderr)
        return 2
    payload = {
        "name": sk["name"],
        "description": sk["desc"],
        "class": sk["cls"],
        "model_visible": not sk["hidden"],
        "path": sk["path"],
        "references": sk["refs"],
        "related": related(skills, sk["name"]),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"name:          {payload['name']}")
    print(f"class:         {payload['class']}")
    print(f"model-visible: {'yes' if payload['model_visible'] else 'no (hidden)'}")
    print(f"path:          {payload['path']}")
    if payload["references"]:
        print(f"references:    {', '.join(payload['references'])}")
    if payload["related"]:
        print(f"related:       {', '.join(payload['related'])}")
    print(f"description:   {payload['description']}")
    if not payload["model_visible"]:
        print("(hidden skills are not in startup metadata; search finds them on demand)")
    return 0


def cmd_stats(skills: list[dict], args) -> int:
    st = stats(skills)
    if args.json:
        print(json.dumps(st, indent=2))
        return 0
    print("Skill catalog stats")
    print(f"  total: {st['total']}  visible: {st['visible']}  hidden: {st['hidden']}")
    n_local = sum(1 for s in skills if s.get("local"))
    if n_local:
        print(f"  machine-local (git-ignored; excluded from generated catalogs): {n_local}")
    print(f"  visible metadata: {st['visible_chars']} chars (~{st['visible_tokens_approx']} tokens)")
    for c in sorted(st["classes"]):
        print(f"  class {c:13} {st['classes'][c]}")
    print("  largest visible descriptions:")
    for l in st["largest"]:
        print(f"    {l['desc_chars']:5}  {l['name']}")
    return 0


def build_docs(skills: list[dict]) -> dict[str, str]:
    pub = [s for s in skills if not s.get("local")]
    return {
        DOCS / "skill-catalog.md": build_skill_catalog_md(pub),
    }


def cmd_generate(skills: list[dict], args) -> int:
    targets = build_docs(skills)
    if args.check:
        stale = []
        for path, content in targets.items():
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(BASE)))
        if stale:
            print("GENERATED CATALOG STALE — rerun: python3 scripts/skill-catalog.py generate")
            for s in stale:
                print(f"  - {s}")
            return 1
        print("generated catalogs up to date")
        return 0
    DOCS.mkdir(exist_ok=True)
    for path, content in targets.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(BASE)}")
    return 0


def selftest() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        skills_dir = root / "skills"
        pack_dir = root / "foundation-pack"
        (skills_dir / "dashboard-patterns").mkdir(parents=True)
        (skills_dir / "unrelated-noise-skill").mkdir(parents=True)
        (skills_dir / "dashboard-patterns" / "SKILL.md").write_text(
            "---\nname: dashboard-patterns\ndescription: Use when building dashboard settings pages and layout patterns.\n"
            "disable-model-invocation: true\n---\n# Dashboard patterns\n",
            encoding="utf-8",
        )
        (skills_dir / "unrelated-noise-skill" / "SKILL.md").write_text(
            "---\nname: unrelated-noise-skill\ndescription: Use when parsing COBOL batch files.\n"
            "disable-model-invocation: true\n---\n# Noise\n",
            encoding="utf-8",
        )
        (pack_dir / "dashboard-settings-foundation").mkdir(parents=True)
        (pack_dir / "unrelated-noise-foundation").mkdir(parents=True)
        (pack_dir / "dashboard-settings-foundation" / "SKILL.md").write_text(
            "---\nname: dashboard-settings-foundation\ndescription: Dashboard settings UI seams and form validation patterns.\n---\n",
            encoding="utf-8",
        )
        (pack_dir / "unrelated-noise-foundation" / "SKILL.md").write_text(
            "---\nname: unrelated-noise-foundation\ndescription: Legacy mainframe terminal emulation.\n---\n",
            encoding="utf-8",
        )
        skills = scan(skills_dir=skills_dir)
        foundations = scan_foundations(pack_dir=pack_dir)
        query = "dashboard settings page"
        skill_hits = search(skills, query, 5)
        foundation_hits = search_foundations(foundations, query, 5)
        if not skill_hits or skill_hits[0]["name"] != "dashboard-patterns":
            print(f"FAIL skill search expected dashboard-patterns first, got {skill_hits}")
            ok = False
        else:
            print("PASS skill metadata search ranks relevant hidden skill")
        if any(h["name"] == "unrelated-noise-skill" for h in skill_hits[:2]):
            print(f"FAIL noise skill ranked too high: {skill_hits[:2]}")
            ok = False
        if not foundation_hits or foundation_hits[0]["name"] != "dashboard-settings-foundation":
            print(f"FAIL foundation search expected dashboard-settings-foundation first, got {foundation_hits}")
            ok = False
        else:
            print("PASS foundation metadata search ranks relevant foundation")
        if any(h["name"] == "unrelated-noise-foundation" for h in foundation_hits[:2]):
            print(f"FAIL noise foundation ranked too high: {foundation_hits[:2]}")
            ok = False
        (skills_dir / "arduino-trap").mkdir(exist_ok=True)
        (skills_dir / "arduino-trap" / "SKILL.md").write_text(
            "---\nname: arduino-trap\ndescription: Use when programming Arduino microcontroller hardware.\n"
            "disable-model-invocation: true\n---\n# Trap\n",
            encoding="utf-8",
        )
        (pack_dir / "react-foundation").mkdir(exist_ok=True)
        (pack_dir / "react-foundation" / "SKILL.md").write_text(
            "---\nname: react-foundation\ndescription: React component patterns and UI composition.\n---\n",
            encoding="utf-8",
        )
        skills = scan(skills_dir=skills_dir)
        foundations = scan_foundations(pack_dir=pack_dir)
        ui_hits = search(skills, "ui", 3)
        if ui_hits and ui_hits[0]["name"] == "arduino-trap":
            print(f"FAIL short token ui matched substring inside arduino: {ui_hits}")
            ok = False
        else:
            print("PASS short token ui avoids arduino substring trap")
        react_hits = search_foundations(foundations, "react ui", 3)
        if not react_hits or react_hits[0]["name"] != "react-foundation":
            print(f"FAIL react ui expected react-foundation first, got {react_hits}")
            ok = False
        else:
            print("PASS react ui ranks react-foundation first")
    print("skill-catalog selftest: PASS" if ok else "skill-catalog selftest: FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="list skills with class and visibility")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--hidden", action="store_true")
    p.add_argument("--class", dest="klass", choices=CLASSES)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search", help="scored skill catalog search (metadata + light body)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search-foundations", help="scored foundation-pack search (metadata only)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search-leverage", help="search skills and foundations together")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="inspect one skill")
    p.add_argument("name")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("stats", help="catalog and context-budget stats")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("generate", help="write docs/skill-catalog.md")
    p.add_argument("--check", action="store_true", help="verify generated docs are current")
    args = ap.parse_args()
    skills = scan()
    foundations = scan_foundations()
    dispatch = {
        "list": lambda: cmd_list(skills, args),
        "search": lambda: cmd_search(skills, args),
        "search-foundations": lambda: cmd_search_foundations(foundations, args),
        "search-leverage": lambda: cmd_search_leverage(skills, foundations, args),
        "show": lambda: cmd_show(skills, args),
        "stats": lambda: cmd_stats(skills, args),
        "generate": lambda: cmd_generate(skills, args),
    }
    return dispatch[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())

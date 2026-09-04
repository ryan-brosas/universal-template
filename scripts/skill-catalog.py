#!/usr/bin/env python3
"""skill-catalog.py — catalog maintenance over the unified skills tree.

Optional human-facing catalog tooling (list, search, show, stats, generate).
The filesystem and each skill's frontmatter are canonical. Models should use
native filesystem or host discovery during ordinary work. Zero dependencies.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
DOCS = BASE / "docs"
TOKEN_CHARS = 4
DESC_TRUNC = 160


def _load_skill_metadata():
    spec = importlib.util.spec_from_file_location(
        "skill_validator", str(Path(__file__).with_name("skill-validator.py")))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_METADATA = _load_skill_metadata()
parse_frontmatter = _METADATA.parse_frontmatter
CLASSES = ("entry", "internal", "manual", "vendor")
KINDS = ("skill", "foundation")
FOUNDATION_KIND = "foundation"

STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "and", "or",
    "how", "does", "do", "is", "are", "our", "we", "my", "me", "use", "when",
    "find", "show", "skill", "skills", "have", "list", "what", "which",
}


def scan() -> list[dict]:
    local_dirs = _METADATA.git_ignored_dirs(SKILLS)
    out: list[dict] = []
    if not SKILLS.is_dir():
        return out
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        sm = d / "SKILL.md"
        if not sm.is_file():
            continue
        text = sm.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        hidden = str(fm.get("disable-model-invocation", "")).strip().lower() == "true"
        invocation = fm.get("invocation")
        kind = fm.get("kind") or "skill"
        out.append({
            "name": fm.get("name", d.name),
            "folder": d.name,
            "desc": fm.get("description", ""),
            "kind": kind,
            "hidden": hidden,
            "local": d.name in local_dirs,
            "cls": invocation,
            "path": str(sm),
            "body": text,
            "body_low": text.lower()[:20000],
            "refs": sorted(p.name for p in (d / "references").glob("*.md"))
            if (d / "references").is_dir() else [],
        })
    return out


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", query.lower())
            if t not in STOPWORDS and len(t) > 1]


def word_tokens(text: str) -> set[str]:
    return {chunk for chunk in re.split(r"[^a-z0-9]+", text.lower()) if chunk}


def _phrase_in_text(phrase: str, text: str) -> bool:
    if not phrase or len(phrase) <= 3:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b"
    return re.search(pattern, text.lower()) is not None


def score_skill(skill: dict, toks: list[str], query_low: str) -> tuple[float, list[str]]:
    s = 0.0
    why: list[str] = []
    name_low = skill["name"].lower()
    desc_low = skill["desc"].lower()
    name_tokens = word_tokens(name_low)
    desc_tokens = word_tokens(desc_low)
    body_tokens = word_tokens(skill["body_low"])
    if query_low and query_low == name_low:
        s += 12.0
        why.append("exact name")
    for t in toks:
        if t in name_tokens:
            s += 4.0
            why.append("name:" + t)
        if t in desc_tokens:
            s += 2.0
            why.append("desc:" + t)
        if t in body_tokens:
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


def search(skills: list[dict], query: str, limit: int) -> list[dict]:
    toks = tokens(query)
    q_low = re.sub(r"[^a-z0-9 ]", " ", query.lower()).strip()
    q_low = " ".join(q_low.split())
    scored = []
    for sk in skills:
        s, why = score_skill(sk, toks, q_low)
        if s > 0:
            scored.append({"score": s, "why": why, **{k: sk[k] for k in
                          ("name", "kind", "cls", "hidden", "desc", "path")}})
    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]


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
    return sum(
        len(s["name"]) + len(s["desc"])
        for s in skills
        if s["kind"] != FOUNDATION_KIND and not s["hidden"]
    )


def stats(skills: list[dict]) -> dict:
    operational = [s for s in skills if s["kind"] != FOUNDATION_KIND]
    foundations = [s for s in skills if s["kind"] == FOUNDATION_KIND]
    vis = [s for s in operational if not s["hidden"]]
    by_class: dict[str, int] = {}
    for s in operational:
        c = s["cls"] or "unclassified"
        by_class[c] = by_class.get(c, 0) + 1
    largest = sorted(vis, key=lambda s: -len(s["desc"]))[:10]
    loader_words = sorted(len(s["body"].split()) for s in foundations)
    chars = visible_chars(operational)
    return {
        "total": len(operational),
        "visible": len(vis),
        "hidden": len(operational) - len(vis),
        "visible_chars": chars,
        "visible_tokens_approx": chars // TOKEN_CHARS,
        "classes": by_class,
        "largest": [{"name": s["name"], "desc_chars": len(s["desc"])} for s in largest],
        "foundations": {
            "total": len(foundations),
            "visible": sum(not s["hidden"] for s in foundations),
            "loader_words_min": loader_words[0] if loader_words else 0,
            "loader_words_median": loader_words[len(loader_words) // 2] if loader_words else 0,
            "loader_words_max": loader_words[-1] if loader_words else 0,
        },
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
    skills = [s for s in skills if s["kind"] != FOUNDATION_KIND]
    lines = [
        "<!-- GENERATED by scripts/skill-catalog.py (generate). Do not edit by hand; rerun the script. -->",
        "",
        "# Skill Catalog",
        "",
        "Derived from operational `skills/*/SKILL.md` metadata for human browsing.",
        "Models discover skills from the filesystem or the host's native skill surface.",
        "Cold foundations are excluded; see `foundation-catalog.md`.",
        "",
    ]
    st = stats(skills)
    lines.append(f"{st['total']} skills: {st['visible']} visible, {st['hidden']} hidden. "
                 f"Visible startup metadata: ~{st['visible_chars']} chars "
                 f"(~{st['visible_tokens_approx']} tokens).")
    lines.append("")
    sections = [
        ("Entry skills", "entry", "Direct user-facing capabilities; trigger on request."),
        ("Internal", "internal", "Invoked by another capability; hidden from startup metadata."),
        ("Manual specialists", "manual", "Loaded explicitly through native search or inspection; hidden from startup metadata."),
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
        lines += ["## Invalid metadata", "",
                  "These skills lack local invocation metadata: "
                  + ", ".join(f"`{n}`" for n in unclassified), ""]
    return "\n".join(lines)


def build_foundation_catalog_md(skills: list[dict]) -> str:
    foundations = [s for s in skills if s["kind"] == FOUNDATION_KIND]
    lines = [
        "<!-- GENERATED by scripts/skill-catalog.py (generate). Do not edit by hand; rerun the script. -->",
        "",
        "# Foundation Catalog",
        "",
        "Cold, source-specific, revision-pinned evidence under `skills/*-foundation/`.",
        "Foundations are manual and hidden: search explicitly, open the topic index,",
        "then load one matching capsule. Current source and tests outrank them.",
        "",
        f"{len(foundations)} foundations. They are excluded from the operational skill table and startup counts.",
        "",
    ]
    table = ["| Foundation | Description |", "|---|---|"]
    for s in foundations:
        desc = _clean(s["desc"])
        if len(desc) > DESC_TRUNC:
            desc = desc[:DESC_TRUNC - 1].rstrip() + "..."
        table.append(
            f"| [`{s['name']}`](../skills/{s['folder']}/SKILL.md) | {desc.replace('|', chr(92) + '|')} |"
        )
    lines += _align_md_table(table) + [""]
    return "\n".join(lines)


def cmd_list(skills: list[dict], args) -> int:
    rows = skills
    if args.visible:
        rows = [s for s in rows if not s["hidden"]]
    if args.hidden:
        rows = [s for s in rows if s["hidden"]]
    if args.klass:
        rows = [s for s in rows if s["cls"] == args.klass]
    if args.kind:
        rows = [s for s in rows if s["kind"] == args.kind]
    if args.json:
        print(json.dumps([{k: s[k] for k in ("name", "kind", "cls", "hidden", "desc", "path")}
                          for s in rows], indent=2))
        return 0
    for s in rows:
        vis = "hidden" if s["hidden"] else "VISIBLE"
        local = " machine-local" if s.get("local") else ""
        print(f"{s['kind']:10} {s['cls'] or 'unclassified':12} {vis:7} {s['name']}{local}")
    print(f"-- {len(rows)} entries", file=sys.stderr)
    return 0


def cmd_search(skills: list[dict], args) -> int:
    hits = search(skills, args.query, args.limit)
    if args.json:
        print(json.dumps(hits, indent=2))
        return 0
    if not hits:
        print(f"no matches for: {args.query!r}")
        return 0
    print(f"catalog candidates for: {args.query!r}")
    for h in hits:
        vis = "hidden" if h["hidden"] else "visible"
        reason = ", ".join(h["why"][:4])
        print(f"  {h['score']:6.1f}  {h['name']:40} {h['kind']:10} {h['cls'] or 'unclassified':9} {vis:7} {reason}")
    print("Load only the candidate you need (skills/<name>/SKILL.md).")
    return 0


def cmd_show(skills: list[dict], args) -> int:
    sk = next((s for s in skills if s["name"] == args.name or s["folder"] == args.name), None)
    if sk is None:
        print(f"no such skill: {args.name}", file=sys.stderr)
        return 2
    payload = {
        "name": sk["name"],
        "description": sk["desc"],
        "kind": sk["kind"],
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
    print(f"kind:          {payload['kind']}")
    print(f"class:         {payload['class']}")
    print(f"model-visible: {'yes' if payload['model_visible'] else 'no (hidden)'}")
    print(f"path:          {payload['path']}")
    if payload["references"]:
        print(f"references:    {', '.join(payload['references'])}")
    if payload["related"]:
        print(f"related:       {', '.join(payload['related'])}")
    print(f"description:   {payload['description']}")
    if payload["kind"] == FOUNDATION_KIND:
        print("(cold foundation: open references/index.md, then load one matching capsule)")
    elif not payload["model_visible"]:
        print("(hidden skills are not in startup metadata; host discovery finds them on demand)")
    return 0


def cmd_stats(skills: list[dict], args) -> int:
    st = stats(skills)
    if args.json:
        print(json.dumps(st, indent=2))
        return 0
    print("Skill catalog stats")
    print(f"  operational: {st['total']}  visible: {st['visible']}  hidden: {st['hidden']}")
    foundation_stats = st["foundations"]
    print(f"  foundations: {foundation_stats['total']}  visible: {foundation_stats['visible']}"
          f"  loader words min/median/max: {foundation_stats['loader_words_min']}/"
          f"{foundation_stats['loader_words_median']}/{foundation_stats['loader_words_max']}")
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


def cmd_selftest(skills: list[dict], _args) -> int:
    foundations = [s for s in skills if s["kind"] == FOUNDATION_KIND and not s.get("local")]
    operational = [s for s in skills if s["kind"] != FOUNDATION_KIND and not s.get("local")]
    if not foundations or not operational:
        print("selftest: both operational skills and foundations are required", file=sys.stderr)
        return 1
    sample = foundations[0]
    hits = search(skills, sample["name"], 1)
    if not hits or hits[0]["name"] != sample["name"] or hits[0]["kind"] != FOUNDATION_KIND:
        print("selftest: exact foundation search failed", file=sys.stderr)
        return 1
    st = stats([*operational, *foundations])
    if st["total"] != len(operational) or st["foundations"]["total"] != len(foundations):
        print("selftest: kind-separated stats failed", file=sys.stderr)
        return 1
    skill_doc = build_skill_catalog_md([*operational, *foundations])
    foundation_doc = build_foundation_catalog_md([*operational, *foundations])
    sample_link = f"../skills/{sample['name']}/SKILL.md"
    if sample_link in skill_doc or sample_link not in foundation_doc:
        print("selftest: generated catalog separation failed", file=sys.stderr)
        return 1
    if any(f"../skills/{s['name']}/SKILL.md" in foundation_doc for s in operational):
        print("selftest: operational skill leaked into foundation catalog", file=sys.stderr)
        return 1
    print("SKILL CATALOG SELFTEST PASS")
    return 0


def build_docs(skills: list[dict]) -> dict[str, str]:
    pub = [s for s in skills if not s.get("local")]
    return {
        DOCS / "skill-catalog.md": build_skill_catalog_md(pub),
        DOCS / "foundation-catalog.md": build_foundation_catalog_md(pub),
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="list skills with class and visibility")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--hidden", action="store_true")
    p.add_argument("--class", dest="klass", choices=CLASSES)
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search", help="scored catalog search (maintainer/explicit queries)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="inspect one skill")
    p.add_argument("name")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("stats", help="catalog and context-budget stats")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("generate", help="write generated skill and foundation catalogs")
    p.add_argument("--check", action="store_true", help="verify generated docs are current")
    sub.add_parser("selftest", help="verify kind-aware search, stats, and catalog separation")
    args = ap.parse_args()
    skills = scan()
    return {"list": cmd_list, "search": cmd_search, "show": cmd_show,
            "stats": cmd_stats, "generate": cmd_generate,
            "selftest": cmd_selftest}[args.cmd](skills, args)


if __name__ == "__main__":
    sys.exit(main())

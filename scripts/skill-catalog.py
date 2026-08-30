#!/usr/bin/env python3
"""skill-catalog.py — deterministic discovery over the local skill catalog.

The catalog (skills/*/SKILL.md) is far larger than startup metadata should
carry. Visible skills are deliberately few; everything else (foundations,
specialists, internal mechanics) stays hidden and is found here:

    list / search / show / stats / generate

Classification (entry / router / internal / cold / vendor) is owned by
catalog-quality.py; this tool reports it and generates the human catalogs.
Zero dependencies.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = BASE / "skills"
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

# Mechanical foundation buckets for the generated human catalog. First keyword
# hit wins; leftovers land in Other. Classification stays name/description
# based — no per-foundation manual curation.
BUCKETS = [
    ("Agent & LLM frameworks", (
        "agent", "agno", "autogen", "crewai", "langgraph", "llm", "openai",
        "swarm", "semantic-kernel", "smolagents", "pydantic-ai", "mastra",
        "camel", "ell", "gpt-", "litellm", "mem0", "graphiti", "cognee",
        "cline", "continue", "openhands", "gpt-engineer", "roo-", "sweep",
        "cuga", "locoagent", "awaithumans", "agent-s")),
    ("Web frameworks & services", (
        "django", "flask", "fastapi", "starlette", "rails", "spring",
        "laravel", "symfony", "express", "nest-", "uvicorn", "requests",
        "server-", "wordpress", "drupal", "magento", "october", "strapi",
        "ghost", "directus", "payload", "tooljet")),
    ("Frontend", (
        "react", "vue-", "svelte", "angular", "tailwind", "shadcn", "radix",
        "dnd-kit", "framer", "recharts", "visx", "headlessui", "htmx",
        "rsbuild", "solid-", "tanstack", "ui-ant", "ui-daisyui", "eslint",
        "biome")),
    ("Data & databases", (
        "duckdb", "milvus", "qdrant", "chroma", "weaviate", "lancedb",
        "txtai", "supabase", "postgres", "mongodb", "meilisearch",
        "typesense", "ragflow", "graphrag", "superset", "airflow", "dagster",
        "prefect", "celery", "turso", "codedb")),
    ("Browser & automation", (
        "browser", "playwright", "crawl", "scrap", "zendriver", "undetectable",
        "ufo-", "theagenticbrowser", "open-computer-use", "screenity")),
    ("Infrastructure & ops", (
        "cloudflare", "railway", "coolify", "docker", "kubernetes", "k8s",
        "cap-", "dokploy", "mailcow", "postal", "listmonk", "healthchecks",
        "uptime", "easyappointments")),
    ("Developer tooling", (
        "aider", "codex", "mcp-", "pi-", "dsh-", "opencode", "inspo-",
        "skills-", "billion-context", "codebase-memory", "jetbrains",
        "qodana", "mike-", "pdf-")),
    ("Security", ("webappsec", "vaultwarden", "aliasvault", "security")),
    ("Content & docs", ("markdown", "docmost", "joplin", "notion", "outline",
                         "paperqa", "storm-")),
    ("Applications & products", (
        "appflowy", "baserow", "nocodb", "teable", "grist", "chatwoot",
        "frezier", "freescout", "plane-", "twenty-", "relaticle", "lemmy",
        "dub-", "growchief", "openoutreach", "openoats", "meetily",
        "linkforty", "georank", "geoready", "openreplay", "penpot",
        "kdenlive", "sharex", "umami", "isso-", "changedetection", "rallly",
        "vercel", "affine", "apitable", "nexus", "os-clovy", "palmier",
        "quickbeam", "scout-", "jobspy", "linkedin", "maximo", "humanizer",
        "fallow", "localterm", "tom-", "opensrc", "nexus-public")),
]


def scan() -> list[dict]:
    # One owner for the tracked-set rule: catalog-quality.git_ignored_dirs.
    local_dirs = _CQ.git_ignored_dirs(SKILLS)
    out: list[dict] = []
    for d in sorted(SKILLS.iterdir()):
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


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", query.lower())
            if t not in STOPWORDS and len(t) > 1]


def score_skill(skill: dict, toks: list[str], query_low: str) -> tuple[float, list[str]]:
    s = 0.0
    why: list[str] = []
    name_low = skill["name"].lower()
    desc_low = skill["desc"].lower()
    if query_low and query_low == name_low:
        s += 12.0
        why.append("exact name")
    for t in toks:
        if t in name_low:
            s += 4.0
            why.append("name:" + t)
        if t in desc_low:
            s += 2.0
            why.append("desc:" + t)
        if t in skill["body_low"]:
            s += 0.5
    if query_low and len(query_low) > 3 and query_low in desc_low:
        s += 5.0
        why.append("desc phrase")
    if query_low and query_low in name_low:
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
                          ("name", "cls", "hidden", "desc", "path")}})
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


def foundation_bucket(name: str, desc_low: str) -> str:
    hay = name.lower()
    for label, keys in BUCKETS:
        for k in keys:
            if k in hay:
                return label
    for label, keys in BUCKETS:
        for k in keys:
            if k in desc_low[:400]:
                return label
    return "Other"


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
    """Generated docs stay house-style clean: no em dashes in prose."""
    return desc.replace("\u2014", "-")


def _md_row(s: dict) -> str:
    desc = _clean(s["desc"])
    if len(desc) > DESC_TRUNC:
        desc = desc[:DESC_TRUNC - 1].rstrip() + "..."
    desc = desc.replace("|", "\\|")
    vis = "hidden" if s["hidden"] else "visible"
    return f"| [`{s['name']}`](../skills/{s['folder']}/SKILL.md) | {s['cls'] or 'unclassified'} | {vis} | {desc} |"


def build_skill_catalog_md(skills: list[dict]) -> str:
    lines = [
        "<!-- GENERATED by scripts/skill-catalog.py (generate). Do not edit by hand; rerun the script. -->",
        "",
        "# Skill Catalog",
        "",
        "Derived from `skills/*/SKILL.md` metadata. Discovery tool:",
        "`python3 scripts/skill-catalog.py search \"<topic>\"`.",
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
        ("Cold specialists", "cold_nonfoundation", "Rare specialists; searchable here, not loaded every session."),
        ("Vendor-managed", "vendor", "Installed and updated by their vendor; visibility follows integration."),
    ]
    for title, key, blurb in sections:
        rows = [s for s in skills if s["cls"] == key] if not key.endswith("nonfoundation") \
            else [s for s in skills if s["cls"] == "cold" and not s["folder"].endswith("-foundation")]
        if not rows:
            continue
        lines += [f"## {title}", "", blurb, "",
                  "| Skill | Class | Visible | Description |", "|---|---|---|---|"]
        lines += [_md_row(s) for s in rows]
        lines.append("")
    founds = [s for s in skills if s["folder"].endswith("-foundation")]
    lines += ["## Foundations", "",
              f"{len(founds)} foundation leaves (all hidden, class cold) are indexed in "
              "[foundation-catalog.md](foundation-catalog.md). Search them with "
              "`python3 scripts/foundation-search.py \"<topic>\"` or "
              "`python3 scripts/skill-catalog.py search \"<topic>\"`. Source repositories "
              "in `<project>/reference/<repo>/` come first; foundations are the cold fallback.", ""]
    unclassified = [s["name"] for s in skills if s["cls"] is None]
    if unclassified:
        lines += ["## Unclassified", "",
                  "These lack a class (catalog-quality fails on unclassified visible skills): "
                  + ", ".join(f"`{n}`" for n in unclassified), ""]
    return "\n".join(lines)


def build_foundation_catalog_md(skills: list[dict]) -> str:
    founds = [s for s in skills if s["folder"].endswith("-foundation")]
    lines = [
        "<!-- GENERATED by scripts/skill-catalog.py (generate). Do not edit by hand; rerun the script. -->",
        "",
        "# Foundation Catalog",
        "",
        f"{len(founds)} hidden foundation leaves, grouped mechanically by name/description "
        "keywords. Buckets are a human-navigation aid; deterministic search remains:",
        "`python3 scripts/foundation-search.py \"<topic>\"`.",
        "",
    ]
    groups: dict[str, list[dict]] = {}
    for s in founds:
        groups.setdefault(foundation_bucket(s["folder"], s["desc"].lower()), []).append(s)
    for label in [l for l, _ in BUCKETS] + ["Other"]:
        rows = groups.get(label)
        if not rows:
            continue
        lines += [f"## {label} ({len(rows)})", ""]
        for s in sorted(rows, key=lambda x: x["folder"]):
            desc = _clean(s["desc"])
            if len(desc) > 120:
                desc = desc[:119].rstrip() + "..."
            lines.append(f"- [`{s['folder']}`](../skills/{s['folder']}/SKILL.md) - {desc}")
        lines.append("")
    return "\n".join(lines)


def cmd_list(skills: list[dict], args) -> int:
    rows = skills
    if args.visible:
        rows = [s for s in rows if not s["hidden"]]
    if args.hidden:
        rows = [s for s in rows if s["hidden"]]
    if args.foundations:
        rows = [s for s in rows if s["folder"].endswith("-foundation")]
    if args.klass:
        rows = [s for s in rows if s["cls"] == args.klass]
    if args.category:
        cat = args.category.lower()
        if cat in CLASSES:
            rows = [s for s in rows if s["cls"] == cat]
        else:
            rows = [s for s in rows
                    if foundation_bucket(s["folder"], s["desc"].lower()).lower().startswith(cat)
                    or cat in foundation_bucket(s["folder"], s["desc"].lower()).lower()]
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
        print(f"no matches for: {args.query!r}")
        return 0
    print(f"catalog candidates for: {args.query!r}")
    for h in hits:
        vis = "hidden" if h["hidden"] else "visible"
        reason = ", ".join(h["why"][:4])
        print(f"  {h['score']:6.1f}  {h['name']:40} {h['cls'] or 'unclassified':9} {vis:7} {reason}")
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
        print("(hidden skills are not in startup metadata; search or explicit invocation finds them)")
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
    """Generated catalogs cover the tracked catalog only: machine-local
    (git-ignored) skills are excluded so a clean CI checkout regenerates
    byte-identical docs."""
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
    p.add_argument("--foundations", action="store_true")
    p.add_argument("--class", dest="klass", choices=CLASSES)
    p.add_argument("--category", help="class name or foundation bucket substring")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search", help="scored catalog search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="inspect one skill")
    p.add_argument("name")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("stats", help="catalog and context-budget stats")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("generate", help="write docs/skill-catalog.md + docs/foundation-catalog.md")
    p.add_argument("--check", action="store_true", help="verify generated docs are current")
    args = ap.parse_args()
    skills = scan()
    return {"list": cmd_list, "search": cmd_search, "show": cmd_show,
            "stats": cmd_stats, "generate": cmd_generate}[args.cmd](skills, args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""skill-catalog.py — catalog maintenance over the unified skills tree.

Optional human-facing catalog tooling (list, search, show, stats, invocation, generate).
The filesystem and each skill's frontmatter are canonical. Models should use
native filesystem or host discovery during ordinary work. PyYAML is shared with
the strict skill validator.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import importlib.util
import json
import os
import re
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
DOCS = BASE / "docs"
CONTEXT_BUDGET = BASE / "config/context-budget.json"
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
FOUNDATION_DISCOVERY_HINT = (
    "Inspect the topic map; search reference filenames/headings; load 1-3 likely capsules. "
    "Use references/index.md only if discovery remains ambiguous."
)

STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "and", "or",
    "how", "does", "do", "is", "are", "our", "we", "my", "me", "use", "when",
    "find", "show", "skill", "skills", "have", "list", "what", "which",
}


def context_surface(kind: str, invocation: str | None, hidden: bool) -> str:
    if kind != FOUNDATION_KIND and invocation == "entry" and not hidden:
        return "hot"
    return "cold"


def tracked_skill_paths(root: Path) -> set[Path]:
    """Enumerate index paths, never infer publication from workspace contents."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "*/SKILL.md"],
            capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("Git tracking unavailable; publication inputs cannot be established") from exc
    return {root / os.fsdecode(raw) for raw in result.stdout.split(b"\0")
            if raw and len(Path(os.fsdecode(raw)).parts) == 2
            and not Path(os.fsdecode(raw)).parts[0].startswith(".")}


def scan(tracked_only: bool = False, root: Path = SKILLS) -> list[dict]:
    try:
        tracked = tracked_skill_paths(root)
    except ValueError:
        if tracked_only:
            raise
        print("WARNING: Git tracking unavailable; discovery results treated as local", file=sys.stderr)
        tracked = set()
    out: list[dict] = []
    candidates = sorted(tracked) if tracked_only else sorted(root.glob("*/SKILL.md"))
    for sm in candidates:
        d = sm.parent
        if d.name.startswith("."):
            continue
        try:
            text = sm.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            type_errors = _METADATA.metadata_type_errors(sm, fm)
            if type_errors:
                raise ValueError("; ".join(type_errors))
        except (OSError, UnicodeError, ValueError) as exc:
            diagnostic = f"{sm}: {exc}"
            if tracked_only:
                raise ValueError(diagnostic) from exc
            print(f"WARNING: skipped skill: {diagnostic}", file=sys.stderr)
            continue
        hidden = fm.get("disable-model-invocation", False) is True
        invocation = fm.get("invocation")
        kind = fm.get("kind") or "skill"
        surface = context_surface(kind, invocation, hidden)
        out.append({
            "name": fm.get("name", d.name),
            "folder": d.name,
            "desc": fm.get("description", ""),
            "kind": kind,
            "hidden": hidden,
            "surface": surface,
            "local": sm not in tracked,
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
                          ("name", "kind", "cls", "hidden", "surface", "local", "desc", "path")}})
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


def load_context_budget(path: Path = CONTEXT_BUDGET) -> dict:
    """Load and validate the canonical static-context budget."""
    value = json.loads(path.read_text(encoding="utf-8"))
    required = (
        ("global_instructions", "max_chars"),
        ("hot", "max_skills"),
        ("hot", "max_metadata_chars"),
        ("combined", "max_chars"),
    )
    for section, key in required:
        number = value.get(section, {}).get(key)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise ValueError(f"{path}: {section}.{key} must be a non-negative integer")
    divisor = value.get("token_estimate_divisor")
    if not isinstance(divisor, int) or isinstance(divisor, bool) or divisor <= 0:
        raise ValueError(f"{path}: token_estimate_divisor must be a positive integer")
    instruction_path = value.get("global_instructions", {}).get("path")
    if not isinstance(instruction_path, str) or not instruction_path:
        raise ValueError(f"{path}: global_instructions.path must be a non-empty string")
    return value


def context_surfaces(skills: list[dict], token_divisor: int) -> dict:
    """Return disjoint startup (hot) and on-demand (cold) identities."""
    hot_rows = [s for s in skills if s["surface"] == "hot"]
    cold_rows = [s for s in skills if s["surface"] == "cold"]
    hot = sorted(s["name"] for s in hot_rows)
    cold = sorted(s["name"] for s in cold_rows)
    chars = sum(len(s["name"]) + len(s["desc"]) for s in hot_rows)
    return {
        "hot": hot,
        "cold": cold,
        "overlap": sorted(set(hot) & set(cold)),
        "hot_count": len(hot),
        "cold_count": len(cold),
        "hot_chars": chars,
        "hot_tokens_approx": chars // token_divisor,
        "cold_operational": sum(s["kind"] != FOUNDATION_KIND for s in cold_rows),
        "cold_foundations": sum(s["kind"] == FOUNDATION_KIND for s in cold_rows),
    }


def stats(skills: list[dict]) -> dict:
    operational = [s for s in skills if s["kind"] != FOUNDATION_KIND]
    foundations = [s for s in skills if s["kind"] == FOUNDATION_KIND]
    budget = load_context_budget()
    surfaces = context_surfaces(skills, budget["token_estimate_divisor"])
    hot_rows = [s for s in operational if s["surface"] == "hot"]
    by_class: dict[str, int] = {}
    for skill in operational:
        invocation = skill["cls"] or "unclassified"
        by_class[invocation] = by_class.get(invocation, 0) + 1
    largest = sorted(hot_rows, key=lambda skill: -len(skill["desc"]))[:10]
    loader_words = sorted(len(skill["body"].split()) for skill in foundations)
    return {
        "total": len(operational),
        "hot": len(hot_rows),
        "cold": surfaces["cold_operational"],
        "visible": sum(not skill["hidden"] for skill in operational),
        "hidden": sum(skill["hidden"] for skill in operational),
        "hot_chars": surfaces["hot_chars"],
        "hot_tokens_approx": surfaces["hot_tokens_approx"],
        "context": surfaces,
        "classes": by_class,
        "largest": [
            {"name": skill["name"], "desc_chars": len(skill["desc"])}
            for skill in largest
        ],
        "foundations": {
            "total": len(foundations),
            "visible": sum(not skill["hidden"] for skill in foundations),
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
    return f"| [`{s['name']}`](../skills/{s['folder']}/SKILL.md) | {s['cls'] or 'unclassified'} | {s['surface']} | {desc} |"


def _split_md_row(row: str) -> list[str]:
    """Split a Markdown row without treating escaped pipes as delimiters."""
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in row.strip()[1:-1]:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _align_md_table(rows: list[str]) -> list[str]:
    parts = [_split_md_row(r) for r in rows]
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
        "Only visible locally owned entry metadata is hot.",
        "Internal, manual, vendor, and foundation capabilities are cold.",
        "",
    ]
    st = stats(skills)
    lines.append(
        f"{st['total']} skills: {st['hot']} hot, {st['cold']} cold. "
        f"Hot startup metadata: ~{st['hot_chars']} chars "
        f"(~{st['hot_tokens_approx']} tokens)."
    )
    lines.append("")
    sections = [
        ("Entry skills", "entry", "Hot direct user-facing capabilities; trigger on request."),
        ("Internal", "internal", "Cold: invoked by another capability and hidden from startup metadata."),
        ("Manual specialists", "manual", "Cold: loaded explicitly through native search or inspection; hidden from startup metadata."),
        ("Vendor-managed", "vendor", "Cold in the generic surface; visibility follows the owning host integration."),
    ]
    for title, key, blurb in sections:
        rows = [s for s in skills if s["cls"] == key]
        if not rows:
            continue
        table = ["| Skill | Class | Surface | Description |", "|---|---|---|---|"] + [_md_row(s) for s in rows]
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
        "This is part of the cold discoverable set and never startup context.",
        "Foundations are manual and hidden. " + FOUNDATION_DISCOVERY_HINT,
        "Current source and tests outrank them.",
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


def filter_list_rows(
    skills: list[dict], *, visible: bool = False, hidden: bool = False,
    klass: str | None = None, kind: str | None = None,
    surface: str | None = None, tracked_only: bool = False,
) -> list[dict]:
    """Apply list filters, including publication-safe local exclusion."""
    rows = [s for s in skills if not tracked_only or not s.get("local")]
    if visible:
        rows = [s for s in rows if not s["hidden"]]
    if hidden:
        rows = [s for s in rows if s["hidden"]]
    if klass:
        rows = [s for s in rows if s["cls"] == klass]
    if kind:
        rows = [s for s in rows if s["kind"] == kind]
    if surface:
        rows = [s for s in rows if s["surface"] == surface]
    return rows


def cmd_list(skills: list[dict], args) -> int:
    rows = filter_list_rows(
        skills, visible=args.visible, hidden=args.hidden, klass=args.klass,
        kind=args.kind, surface=args.surface, tracked_only=args.tracked_only,
    )
    if args.json:
        print(json.dumps([{k: s[k] for k in ("name", "kind", "cls", "hidden", "surface", "local", "desc", "path")}
                          for s in rows], indent=2))
        return 0
    for s in rows:
        vis = "hidden" if s["hidden"] else "VISIBLE"
        local = " machine-local" if s.get("local") else ""
        print(f"{s['surface']:4} {s['kind']:10} {s['cls'] or 'unclassified':12} {vis:7} {s['name']}{local}")
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


def host_visibility(skill: dict) -> str:
    """Host-managed visibility; vendor skills are owned by their integration."""
    if skill["cls"] == "vendor":
        return "owning integration"
    return "visible" if not skill["hidden"] else "hidden"


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
        "invocation_owner": sk["cls"],
        "host_visibility": host_visibility(sk),
        "generic_surface": sk["surface"],
        "path": sk["path"],
        "references": sk["refs"],
        "related": related(skills, sk["name"]),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"name:             {payload['name']}")
    print(f"kind:             {payload['kind']}")
    print(f"invocation-owner: {payload['invocation_owner']}")
    print(f"host-visibility:  {payload['host_visibility']}")
    print(f"generic-surface:  {payload['generic_surface']}")
    print(f"path:             {payload['path']}")
    if payload["references"]:
        print(f"references:    {', '.join(payload['references'])}")
    if payload["related"]:
        print(f"related:       {', '.join(payload['related'])}")
    print(f"description:   {payload['description']}")
    if payload["kind"] == FOUNDATION_KIND:
        print(f"(cold foundation: {FOUNDATION_DISCOVERY_HINT})")
    elif payload["generic_surface"] == "cold":
        print("(cold: not in startup metadata; explicit requests, prompts, project instructions, or host discovery select it)")
    return 0


def invocation_report(skill: dict) -> dict:
    """On-disk Markdown inventory, not measured runtime context or task lift."""
    root = Path(skill["path"]).parent
    refs = root / "references"
    references = []
    skipped = []
    if refs.is_symlink():
        skipped.append("references")
    elif refs.is_dir():
        def raise_walk_error(error):
            raise error

        for directory, dirs, files in os.walk(refs, onerror=raise_walk_error):
            parent = Path(directory)
            for name in sorted(dirs):
                path = parent / name
                if path.is_symlink():
                    skipped.append(path.relative_to(root).as_posix())
                    dirs.remove(name)
            for name in sorted(files):
                path = parent / name
                if path.suffix != ".md":
                    continue
                if path.is_symlink() or not path.is_file():
                    skipped.append(path.relative_to(root).as_posix())
                    continue
                references.append({
                    "path": path.relative_to(root).as_posix(),
                    "chars": len(path.read_text(encoding="utf-8")),
                })
    references.sort(key=lambda item: item["path"])
    return {
        "name": skill["name"],
        "path": skill["path"],
        "loader_chars": len(skill["body"]),
        "loader_words": len(skill["body"].split()),
        "reference_count": len(references),
        "total_reference_chars": sum(item["chars"] for item in references),
        "largest_reference": max(references, key=lambda item: item["chars"], default=None),
        "skipped_reference_paths": sorted(skipped),
        "required_mcp_profile": None,
        "mcp_schema_chars": None,
        "observed_invocation_count": None,
        "observed_average_followup_request_growth_bytes": None,
    }


def cmd_invocation(skills: list[dict], args) -> int:
    if args.limit < 1:
        print("invocation: --limit must be positive", file=sys.stderr)
        return 2
    if args.name:
        rows = [s for s in skills if args.name in (s["name"], s["folder"])]
        if not rows:
            print(f"no such skill: {args.name}", file=sys.stderr)
            return 2
    else:
        rows = [s for s in skills if not s.get("local")]
    rows = sorted(rows, key=lambda s: (-len(s["body"]), s["name"]))[:args.limit]
    try:
        reports = [invocation_report(skill) for skill in rows]
    except (OSError, UnicodeError) as error:
        print(f"invocation: cannot read inventory: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(reports, indent=2))
        return 0
    print("On-disk inventory only; no size gate. Runtime fields are unknown, not zero.")
    for report in reports:
        print(f"\n{report['name']}")
        for key, value in report.items():
            if key == "name":
                continue
            absent = "none" if key == "largest_reference" else "unknown / not measured"
            print(f"  {key}: {value if value is not None else absent}")
    return 0


def cmd_stats(skills: list[dict], args) -> int:
    st = stats(skills)
    if args.json:
        print(json.dumps(st, indent=2))
        return 0
    print("Skill catalog stats")
    print(
        f"  operational: {st['total']}  hot: {st['hot']}  cold: {st['cold']} "
        f" visible: {st['visible']}  hidden: {st['hidden']}"
    )
    foundation_stats = st["foundations"]
    print(f"  foundations: {foundation_stats['total']}  visible: {foundation_stats['visible']}"
          f"  loader words min/median/max: {foundation_stats['loader_words_min']}/"
          f"{foundation_stats['loader_words_median']}/{foundation_stats['loader_words_max']}")
    n_local = sum(1 for s in skills if s.get("local"))
    if n_local:
        print(f"  machine-local (git-ignored; excluded from generated catalogs): {n_local}")
    print(f"  hot metadata: {st['hot_chars']} chars (~{st['hot_tokens_approx']} tokens)")
    for c in sorted(st["classes"]):
        print(f"  class {c:13} {st['classes'][c]}")
    print("  largest hot descriptions:")
    for l in st["largest"]:
        print(f"    {l['desc_chars']:5}  {l['name']}")
    return 0


def context_report(
    skills: list[dict], budget: dict, instruction_path: Path | None = None
) -> dict:
    """Measure the complete static global context against one explicit budget."""
    if instruction_path is None:
        instruction_path = (BASE / budget["global_instructions"]["path"]).resolve()
        try:
            instruction_path.relative_to(BASE.resolve())
        except ValueError as exc:
            raise ValueError("global_instructions.path escapes the repository") from exc
    divisor = budget["token_estimate_divisor"]
    surfaces = context_surfaces(skills, divisor)
    instruction_chars = len(instruction_path.read_text(encoding="utf-8"))
    combined_chars = instruction_chars + surfaces["hot_chars"]
    result = {
        "global_instructions": {
            "path": budget["global_instructions"]["path"],
            "chars": instruction_chars,
            "tokens_approx": instruction_chars // divisor,
            "max_chars": budget["global_instructions"]["max_chars"],
        },
        "hot": {
            "skills": surfaces["hot_count"],
            "names": surfaces["hot"],
            "metadata_chars": surfaces["hot_chars"],
            "tokens_approx": surfaces["hot_tokens_approx"],
            "max_skills": budget["hot"]["max_skills"],
            "max_metadata_chars": budget["hot"]["max_metadata_chars"],
        },
        "combined": {
            "chars": combined_chars,
            "tokens_approx": combined_chars // divisor,
            "max_chars": budget["combined"]["max_chars"],
        },
        "cold": {
            "operational": surfaces["cold_operational"],
            "foundations": surfaces["cold_foundations"],
            "names": surfaces["cold"],
        },
        "overlap": surfaces["overlap"],
        "token_estimate_divisor": divisor,
        "failures": [],
        "warnings": [],
    }
    failures = result["failures"]
    warnings = result["warnings"]
    if result["overlap"]:
        failures.append("hot/cold overlap: " + ", ".join(result["overlap"]))
    if instruction_chars > result["global_instructions"]["max_chars"]:
        failures.append(
            "global_instructions chars "
            f"{instruction_chars} exceed {result['global_instructions']['max_chars']}"
        )
    if result["hot"]["skills"] > result["hot"]["max_skills"]:
        warnings.append(
            f"hot skills {result['hot']['skills']} exceed {result['hot']['max_skills']}"
            " (advisory review threshold, not a publication failure)"
        )
    if result["hot"]["metadata_chars"] > result["hot"]["max_metadata_chars"]:
        failures.append(
            "hot metadata chars "
            f"{result['hot']['metadata_chars']} exceed {result['hot']['max_metadata_chars']}"
        )
    if combined_chars > result["combined"]["max_chars"]:
        failures.append(
            f"combined chars {combined_chars} exceed {result['combined']['max_chars']}"
        )
    return result


def cmd_context(skills: list[dict], args) -> int:
    rows = [skill for skill in skills if not skill.get("local")]
    budget = load_context_budget()
    if args.max_global_chars is not None:
        budget["global_instructions"]["max_chars"] = args.max_global_chars
    if args.max_hot_chars is not None:
        budget["hot"]["max_metadata_chars"] = args.max_hot_chars
    if args.max_hot_skills is not None:
        budget["hot"]["max_skills"] = args.max_hot_skills
    if args.max_combined_chars is not None:
        budget["combined"]["max_chars"] = args.max_combined_chars
    result = context_report(rows, budget)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        global_context = result["global_instructions"]
        hot = result["hot"]
        combined = result["combined"]
        cold = result["cold"]
        print(
            f"global instructions: {global_context['chars']} chars "
            f"(~{global_context['tokens_approx']} tokens)"
        )
        print(
            f"hot: {hot['skills']} skills, {hot['metadata_chars']} metadata chars "
            f"(~{hot['tokens_approx']} tokens)"
        )
        print(
            f"combined static: {combined['chars']} chars "
            f"(~{combined['tokens_approx']} tokens)"
        )
        print(
            f"cold: {cold['operational']} operational, "
            f"{cold['foundations']} foundations"
        )
        print(f"overlap: {len(result['overlap'])}")
        for warning in result["warnings"]:
            print(f"WARN  {warning}")
        for failure in result["failures"]:
            print(f"FAIL  {failure}")
    return 1 if result["failures"] else 0


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
    divisor = load_context_budget()["token_estimate_divisor"]
    surfaces = context_surfaces([*operational, *foundations], divisor)
    if surfaces["overlap"] or surfaces["hot_count"] + surfaces["cold_count"] != len(operational) + len(foundations):
        print("selftest: context surfaces are not exhaustive and disjoint", file=sys.stderr)
        return 1
    expected_surfaces = {
        ("skill", "entry", False): "hot",
        ("skill", "entry", True): "cold",
        ("skill", "internal", True): "cold",
        ("skill", "manual", True): "cold",
        ("skill", "vendor", False): "cold",
        (FOUNDATION_KIND, "manual", True): "cold",
    }
    for inputs, expected in expected_surfaces.items():
        if context_surface(*inputs) != expected:
            print(f"selftest: context classification failed for {inputs}", file=sys.stderr)
            return 1
    fixture = [
        {
            "name": "entry",
            "desc": "x",
            "kind": "skill",
            "surface": "hot",
            "hidden": False,
            "cls": "entry",
            "local": False,
        },
        {
            "name": "vendor",
            "desc": "x",
            "kind": "skill",
            "surface": "cold",
            "hidden": False,
            "cls": "vendor",
            "local": False,
        },
        {
            "name": "local-entry",
            "desc": "x",
            "kind": "skill",
            "surface": "hot",
            "hidden": False,
            "cls": "entry",
            "local": True,
        },
        {
            "name": "foundation",
            "desc": "x",
            "kind": FOUNDATION_KIND,
            "surface": "cold",
            "hidden": True,
            "cls": "manual",
            "local": False,
        },
    ]
    tracked_hot = filter_list_rows(
        fixture, surface="hot", tracked_only=True
    )
    if [skill["name"] for skill in tracked_hot] != ["entry"]:
        print("selftest: tracked hot export included a local skill", file=sys.stderr)
        return 1
    all_hot = filter_list_rows(fixture, surface="hot")
    if {skill["name"] for skill in all_hot} != {"entry", "local-entry"}:
        print("selftest: local skill inspection path missing", file=sys.stderr)
        return 1
    test_budget = {
        "global_instructions": {"path": "AGENTS.md", "max_chars": 5},
        "hot": {"max_skills": 1, "max_metadata_chars": 6},
        "combined": {"max_chars": 11},
        "token_estimate_divisor": 4,
    }
    with tempfile.TemporaryDirectory(prefix="context-budget-") as raw:
        temporary = Path(raw)
        instruction_path = temporary / "AGENTS.md"
        instruction_path.write_text("abcd\n", encoding="utf-8")
        budget_path = temporary / "budget.json"
        budget_path.write_text(json.dumps(test_budget), encoding="utf-8")
        loaded_budget = load_context_budget(budget_path)
        tracked_fixture = [skill for skill in fixture if not skill["local"]]
        report = context_report(tracked_fixture, loaded_budget, instruction_path)
        if report["failures"] or report["combined"]["chars"] != 11:
            print(f"selftest: configured context budget did not pass: {report}", file=sys.stderr)
            return 1
        loaded_budget["global_instructions"]["max_chars"] = 4
        loaded_budget["combined"]["max_chars"] = 10
        failures = context_report(
            tracked_fixture, loaded_budget, instruction_path
        )["failures"]
        if not any(item.startswith("global_instructions") for item in failures):
            print("selftest: global instruction budget failure missing", file=sys.stderr)
            return 1
        if not any(item.startswith("combined") for item in failures):
            print("selftest: combined context budget failure missing", file=sys.stderr)
            return 1
        loaded_budget["global_instructions"]["max_chars"] = 5
        loaded_budget["combined"]["max_chars"] = 11
        loaded_budget["hot"]["max_skills"] = 0
        advisory = context_report(tracked_fixture, loaded_budget, instruction_path)
        if advisory["failures"] or not advisory["warnings"]:
            print("selftest: hot skill count is not advisory", file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory(prefix="invocation-cost-") as raw:
        root = Path(raw) / "sample"
        root.mkdir()
        loader = "---\nname: sample\n---\n# Café 🧪\n"
        skill = {"name": "sample", "path": str(root / "SKILL.md"), "body": loader}
        empty = invocation_report(skill)
        if (empty["loader_chars"] != len(loader)
                or empty["loader_words"] != len(loader.split())
                or empty["reference_count"] != 0
                or empty["total_reference_chars"] != 0
                or empty["largest_reference"] is not None):
            print("selftest: empty/Unicode invocation inventory failed", file=sys.stderr)
            return 1
        refs = root / "references"
        (refs / "nested").mkdir(parents=True)
        (refs / "small.md").write_text("é\n", encoding="utf-8")
        (refs / "nested" / "large.md").write_text("x" * 25000, encoding="utf-8")
        (refs / "image.bin").write_bytes(b"\xff\x00")
        outside = Path(raw) / "outside.md"
        outside.write_bytes(b"\xff")  # Must not be read through a symlink.
        (refs / "external.md").symlink_to(outside)
        populated = invocation_report(skill)
        expected_largest = {"path": "references/nested/large.md", "chars": 25000}
        if (populated["reference_count"] != 2
                or populated["total_reference_chars"] != 25002
                or populated["largest_reference"] != expected_largest
                or populated["skipped_reference_paths"] != ["references/external.md"]):
            print("selftest: recursive invocation inventory or symlink exclusion failed", file=sys.stderr)
            return 1
        unknown_fields = ("required_mcp_profile", "mcp_schema_chars",
                          "observed_invocation_count",
                          "observed_average_followup_request_growth_bytes")
        if any(populated[key] is not None for key in unknown_fields):
            print("selftest: unavailable runtime evidence was invented", file=sys.stderr)
            return 1
        linked_root = Path(raw) / "linked"
        linked_root.mkdir()
        (linked_root / "references").symlink_to(refs, target_is_directory=True)
        linked = invocation_report({**skill, "path": str(linked_root / "SKILL.md")})
        if linked["reference_count"] or linked["skipped_reference_paths"] != ["references"]:
            print("selftest: linked reference root was traversed", file=sys.stderr)
            return 1
        inventory_fixture = [
            {**skill, "folder": "sample", "body": "small"},
            {**skill, "name": "big", "folder": "big", "body": "x" * 50000},
            {**skill, "name": "local", "folder": "local-folder",
             "body": "x" * 60000, "local": True},
        ]
        args = argparse.Namespace(name=None, limit=1, json=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = cmd_invocation(inventory_fixture, args)
        result = json.loads(output.getvalue())
        if status or len(result) != 1 or result[0]["name"] != "big":
            print("selftest: largest/limited/tracked invocation selection failed", file=sys.stderr)
            return 1
        args.name = "local-folder"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = cmd_invocation(inventory_fixture, args)
        if status or json.loads(output.getvalue())[0]["name"] != "local":
            print("selftest: explicit local invocation selection failed", file=sys.stderr)
            return 1
        for name, limit in (("missing", 1), (None, 0)):
            with contextlib.redirect_stderr(io.StringIO()):
                status = cmd_invocation(inventory_fixture, argparse.Namespace(
                    name=name, limit=limit, json=True))
            if status != 2:
                print("selftest: invalid invocation query did not fail", file=sys.stderr)
                return 1
        (refs / "invalid.md").write_bytes(b"\xff")
        with contextlib.redirect_stderr(io.StringIO()):
            status = cmd_invocation(inventory_fixture, args)
        if status != 2:
            print("selftest: unreadable reference did not fail", file=sys.stderr)
            return 1
    escaped = _align_md_table(["| A | B |", "|---|---|", r"| x | one \| two |"])
    if "one \| two" not in escaped[-1] or len(_split_md_row(escaped[-1])) != 2:
        print("selftest: escaped Markdown pipe changed table shape", file=sys.stderr)
        return 1
    print("SKILL CATALOG SELFTEST PASS")
    return 0


def _fixture_skills(root: Path) -> None:
    for name, kind, invocation in (("demo", "skill", "entry"), ("demo-foundation", "foundation", "manual")):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture\nkind: {kind}\n"
            f"invocation: {invocation}\ndisable-model-invocation: {str(kind == FOUNDATION_KIND).lower()}\n---\n# Fixture\n", encoding="utf-8",
        )


def isolated_selftest(args) -> int:
    with tempfile.TemporaryDirectory(prefix="catalog-unit-") as temp:
        root = Path(temp) / "skills"
        _fixture_skills(root)
        # The selftest never dispatches through ambient discovery.
        subprocess.run(["git", "init", "-q", str(root.parent)], check=True)
        subprocess.run(["git", "-C", str(root.parent), "add", "."], check=True)
        rows = scan(tracked_only=True, root=root)
        return cmd_selftest(rows, args)


def fixture_test() -> int:
    """Exercise current CLI discovery, working-tree parsing and publication."""
    with tempfile.TemporaryDirectory(prefix="catalog-cli-") as temp:
        root = Path(temp)
        (root / "scripts").mkdir()
        (root / "config").mkdir()
        for name in ("skill-catalog.py", "skill-validator.py"):
            shutil.copy2(BASE / "scripts" / name, root / "scripts" / name)
        shutil.copy2(CONTEXT_BUDGET, root / "config/context-budget.json")
        (root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        _fixture_skills(root / "skills")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
        env = {**os.environ, "SKILLS_ROOT": str(root / "skills")}

        def run(*args, expected=0):
            result = subprocess.run(
                [sys.executable, str(root / "scripts/skill-catalog.py"), *args],
                cwd=tempfile.gettempdir(), env=env, capture_output=True, text=True,
            )
            if result.returncode != expected:
                raise AssertionError(f"{args}: exit {result.returncode}, expected {expected}\n{result.stdout}\n{result.stderr}")
            return result

        def publication():
            rows = json.loads(run("list", "--surface", "hot", "--tracked-only", "--json").stdout)
            assert [row["name"] for row in rows] == ["demo"]
            run("context", "--json")
            run("generate", "--check")

        run("generate")
        publication()
        for name in ("draft", "ignored"):
            directory = root / "skills" / name
            directory.mkdir()
            (directory / "SKILL.md").write_text("unfinished\n", encoding="utf-8")
        (root / ".gitignore").write_text("skills/ignored/\n", encoding="utf-8")
        valid_local = root / "skills/local"
        valid_local.mkdir()
        (valid_local / "SKILL.md").write_text(
            "---\nname: local\ndescription: valid local\ninvocation: entry\n---\n", encoding="utf-8")
        publication()
        local = run("list", "--json")
        assert {row["name"] for row in json.loads(local.stdout)} == {"demo", "demo-foundation", "local"}
        assert "draft/SKILL.md" in local.stderr and "ignored/SKILL.md" in local.stderr
        run("selftest")
        tracked = root / "skills/demo/SKILL.md"
        tracked.write_text("invalid uncommitted edit\n", encoding="utf-8")
        for args in (("list", "--tracked-only", "--json"), ("context",), ("generate", "--check")):
            assert "demo/SKILL.md" in run(*args, expected=1).stderr
        subprocess.run(["git", "-C", str(root), "add", str(tracked)], check=True)
        assert "demo/SKILL.md" in run("generate", expected=1).stderr
        # Git failure must not promote an external collection to publication.
        shutil.rmtree(root / ".git")
        assert "Git tracking unavailable" in run("context", expected=1).stderr
        assert "Git tracking unavailable" in run("list", "--json").stderr
    print("SKILL CATALOG FIXTURE TEST PASS")
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
    p.add_argument("--surface", choices=("hot", "cold"))
    p.add_argument("--tracked-only", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("search", help="scored catalog search (maintainer/explicit queries)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="inspect one skill")
    p.add_argument("name")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("invocation", help="optional loader/reference inventory; no size gate")
    p.add_argument("name", nargs="?", help="one skill; otherwise largest tracked loaders")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("stats", help="catalog and context-budget stats")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("context", help="measure and optionally gate disjoint hot/cold surfaces")
    p.add_argument("--json", action="store_true")
    p.add_argument("--max-global-chars", type=int)
    p.add_argument("--max-hot-chars", type=int)
    p.add_argument("--max-hot-skills", type=int)
    p.add_argument("--max-combined-chars", type=int)
    p = sub.add_parser("generate", help="write generated skill and foundation catalogs")
    p.add_argument("--check", action="store_true", help="verify generated docs are current")
    sub.add_parser("selftest", help="verify kind-aware search, stats, and catalog separation")
    sub.add_parser("fixture-test", help="test publication isolation through the production CLI")
    args = ap.parse_args()
    if args.cmd == "selftest":
        return isolated_selftest(args)
    if args.cmd == "fixture-test":
        return fixture_test()
    publication = args.cmd in {"generate", "context", "stats"} or getattr(args, "tracked_only", False)
    try:
        skills = scan(tracked_only=publication)
    except ValueError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return {"list": cmd_list, "search": cmd_search, "show": cmd_show,
            "invocation": cmd_invocation, "stats": cmd_stats,
            "context": cmd_context, "generate": cmd_generate,
            "selftest": cmd_selftest}[args.cmd](skills, args)


if __name__ == "__main__":
    sys.exit(main())

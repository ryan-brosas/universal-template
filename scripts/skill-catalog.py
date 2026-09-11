#!/usr/bin/env python3
"""Maintain the tracked skill surface and optional human catalogs.

The filesystem and each skill's frontmatter are canonical. Models use native
filesystem or host discovery; this tool only lists the surface, checks its
static-context contract, and derives human-readable catalogs.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from publication_fixtures import fixture_environment, fixture_git, require, verify_fixture_support

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
        })
    return out


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
    """Return only the counts needed by generated catalog headers."""
    operational = [skill for skill in skills if skill["kind"] != FOUNDATION_KIND]
    foundations = [skill for skill in skills if skill["kind"] == FOUNDATION_KIND]
    budget = load_context_budget()
    surfaces = context_surfaces(skills, budget["token_estimate_divisor"])
    return {
        "total": len(operational),
        "hot": surfaces["hot_count"],
        "cold": surfaces["cold_operational"],
        "hot_chars": surfaces["hot_chars"],
        "hot_tokens_approx": surfaces["hot_tokens_approx"],
        "foundations": {"total": len(foundations)},
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
        {"name": "entry", "desc": "x", "kind": "skill", "surface": "hot",
         "hidden": False, "cls": "entry", "local": False},
        {"name": "vendor", "desc": "x", "kind": "skill", "surface": "cold",
         "hidden": False, "cls": "vendor", "local": False},
        {"name": "local-entry", "desc": "x", "kind": "skill", "surface": "hot",
         "hidden": False, "cls": "entry", "local": True},
        {"name": "foundation", "desc": "x", "kind": FOUNDATION_KIND,
         "surface": "cold", "hidden": True, "cls": "manual", "local": False},
    ]
    tracked_hot = filter_list_rows(fixture, surface="hot", tracked_only=True)
    if [skill["name"] for skill in tracked_hot] != ["entry"]:
        print("selftest: tracked hot export included a local skill", file=sys.stderr)
        return 1
    if {skill["name"] for skill in filter_list_rows(fixture, surface="hot")} != {"entry", "local-entry"}:
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
        failures = context_report(tracked_fixture, loaded_budget, instruction_path)["failures"]
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
        fixture_git(root.parent, "init", "-q")
        fixture_git(root.parent, "add", ".")
        with patch.dict(os.environ, fixture_environment(root.parent), clear=True):
            rows = scan(tracked_only=True, root=root)
        return cmd_selftest(rows, args)


def fixture_test() -> int:
    """Exercise current CLI discovery, working-tree parsing and publication."""
    verify_fixture_support()
    with tempfile.TemporaryDirectory(prefix="catalog-cli-") as temp:
        root = Path(temp)
        (root / "scripts").mkdir()
        (root / "config").mkdir()
        for name in ("skill-catalog.py", "skill-validator.py", "publication_fixtures.py"):
            shutil.copy2(BASE / "scripts" / name, root / "scripts" / name)
        shutil.copy2(CONTEXT_BUDGET, root / "config/context-budget.json")
        (root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        _fixture_skills(root / "skills")
        fixture_git(root, "init", "-q")
        fixture_git(root, "add", ".")
        fixture_git(root, "commit", "-qm", "fixture")
        env = {**fixture_environment(root), "SKILLS_ROOT": str(root / "skills")}

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
            require([row["name"] for row in rows] == ["demo"], "tracked export population changed")
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
        require({row["name"] for row in json.loads(local.stdout)} == {"demo", "demo-foundation", "local"}, "local discovery lost valid candidates")
        require("draft/SKILL.md" in local.stderr and "ignored/SKILL.md" in local.stderr, "draft diagnostics missing")
        run("selftest")
        tracked = root / "skills/demo/SKILL.md"
        marker = "sensitive-" + "catalog-canary"
        for source in (f"description: [{marker}\n", f"{marker}: a\n{marker}: b\n"):
            tracked.write_text("---\n" + source + "---\n", encoding="utf-8")
            for args, expected in (
                (("list", "--json"), 0),
                (("list", "--tracked-only", "--json"), 1),
                (("context",), 1),
                (("generate", "--check"), 1),
            ):
                result = run(*args, expected=expected)
                require(marker not in result.stdout + result.stderr, "diagnostic echoed input")
                require("invalid YAML" in result.stderr, "missing safe YAML diagnostic")
        tracked.write_text("invalid uncommitted edit\n", encoding="utf-8")
        for args in (("list", "--tracked-only", "--json"), ("context",), ("generate", "--check")):
            require("demo/SKILL.md" in run(*args, expected=1).stderr, "invalid working-tree edit not diagnosed")
        fixture_git(root, "add", str(tracked))
        require("demo/SKILL.md" in run("generate", expected=1).stderr, "invalid tracked skill not diagnosed")
        # Git failure must not promote an external collection to publication.
        shutil.rmtree(root / ".git")
        require("Git tracking unavailable" in run("context", expected=1).stderr, "publication inferred an outer Git repository")
        require("Git tracking unavailable" in run("list", "--json").stderr, "local discovery omitted tracking limitation")
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
    parser = sub.add_parser("list", help="list skills with class and visibility")
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--hidden", action="store_true")
    parser.add_argument("--class", dest="klass", choices=CLASSES)
    parser.add_argument("--kind", choices=KINDS)
    parser.add_argument("--surface", choices=("hot", "cold"))
    parser.add_argument("--tracked-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser = sub.add_parser("context", help="measure and gate disjoint hot/cold surfaces")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-global-chars", type=int)
    parser.add_argument("--max-hot-chars", type=int)
    parser.add_argument("--max-hot-skills", type=int)
    parser.add_argument("--max-combined-chars", type=int)
    parser = sub.add_parser("generate", help="write generated skill and foundation catalogs")
    parser.add_argument("--check", action="store_true", help="verify generated docs are current")
    sub.add_parser("selftest", help="verify catalog separation and context contracts")
    sub.add_parser("fixture-test", help="test publication isolation through the production CLI")
    args = ap.parse_args()
    if args.cmd == "selftest":
        return isolated_selftest(args)
    if args.cmd == "fixture-test":
        return fixture_test()
    publication = args.cmd in {"generate", "context"} or getattr(args, "tracked_only", False)
    try:
        skills = scan(tracked_only=publication)
    except ValueError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return {"list": cmd_list, "context": cmd_context, "generate": cmd_generate}[args.cmd](skills, args)

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Catalog quality gate - anti-slop structure plus the context-budget report.

Checks (hard failures exit 1):
- every skill dir has SKILL.md; name matches folder; no duplicate names
- essentials present and indexed in essentials/README.md
- templates inventory matches templates/ on disk
- visibility policy: *-foundation hidden by default, entry skills visible,
  internal helpers hidden (invocation-ownership model)
- context budget: visible skill metadata vs the recorded baseline; growth is a
  warning, growth beyond GROWTH_FAIL is an error until the baseline is updated
  deliberately via --update-baseline

Warnings print but do not fail.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = BASE / "skills"
ESSENTIALS = BASE / "essentials"
TEMPLATES = BASE / "templates"
INVENTORY = BASE / "references" / "templates-inventory.md"
BASELINE = BASE / "scripts" / "context-budget-baseline.json"

DESC_WARN_CHARS = 450      # visible description size worth reporting
GROWTH_FAIL = 1.10         # unexplained growth above baseline fails CI
TOKEN_CHARS = 4            # documented rough estimator; trend metric only

# Invocation-ownership classification (validator-side policy; hosts only read
# disable-model-invocation). Every visible skill must carry an explicit class:
# entry (a user request selects it directly), router (automatic dispatch point),
# or vendor (externally managed). Hidden skills default to cold (searchable
# specialist knowledge) unless listed as internal (another skill/system invokes
# them) — foundations are always cold.
ENTRY_SKILLS = {
    # flow entries
    "project-bootstrap", "brainstorming", "goal-setup", "prototype",
    "leverage-capture", "leverage-playbook", "reference-driven-development",
    "using-git-worktrees", "zoom-out",
    # github / delivery
    "github-repo-setup", "github-actions-engineering", "push-pr",
    "git-workflow-and-versioning", "github-contribution-opportunities",
    # engineering procedures
    "coding-best-practices", "code-cleanup", "debugging-and-error-recovery",
    "test-generation", "security-and-hardening", "api-and-interface-design",
    "system-design-specification", "deprecation-and-migration",
    "improve-codebase-architecture", "farmed-test-harness", "grill-me",
    # authoring / prose gates
    "writing-skills", "house-writing-style",
    # discovery
    "skill-catalog",
    # tool / runtime capabilities
    "cdp", "findata", "gmaps", "gnews", "gsearch", "rsearch", "xsearch",
    "ytdl", "ttdl", "upwork-proposals", "omarchy", "math-schema",
    "mcp-steroid", "gemini-large-context",
}
# Automatic dispatch points: visible because a state or phase routes to them.
ROUTER_SKILLS = {
    "evidence-router", "execution-router", "verification-before-completion",
}
# Internally invoked mechanics: never startup metadata.
INTERNAL_SKILLS = {
    "model-resolution", "veda-lane", "fabric-native-execution",
    "code-foundations", "foundations-workflow", "memory-graph-skill-miner",
    "repo-inspo-organizer", "code-discipline", "agent-code-quality-gate",
    "code-review-and-quality", "quality-gate-methodology",
    "test-driven-development", "source-driven-development",
    "testing-anti-patterns", "documentation-and-adrs", "defense-in-depth",
    "performance-optimization", "practices-to-ci", "root-cause-tracing",
    "codebase-memory", "codex-websearch", "opensrc", "grill-with-docs",
    "fallow",
}
# Externally managed skills (installed/updated by their vendor).
VENDOR_SKILLS = {
    "veda-plan", "veda-plan-implement", "veda-plan-implement-review",
    "veda-deep-plan", "veda-worker",
}


def classify(folder: str, hidden: bool) -> str | None:
    """Mechanical class for a skill (None = unclassified)."""
    if folder.endswith("-foundation"):
        return "cold"
    if folder in VENDOR_SKILLS:
        return "vendor"
    if not hidden:
        if folder in ROUTER_SKILLS:
            return "router"
        if folder in ENTRY_SKILLS:
            return "entry"
        return None
    return "internal" if folder in INTERNAL_SKILLS else "cold"
# Foundations are cold prior-art capsules: hidden unless explicitly allowlisted.
FOUNDATION_ALLOWLIST: set[str] = set()

errors: list[str] = []
warnings: list[str] = []

ESSENTIAL_FILES = [
    "operating-philosophy.md",
    "guiding-small-model.md",
    "steer-outcomes-not-behavior.md",
    "stack-your-leverage.md",
    "enforce-code-quality-mechanically.md",
    "how-to-build-good-tests.md",
    "openviking-foundation.md",
    "README.md",
]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[4:end] if text.startswith("---\n") else text[3:end]
    fm: dict[str, str] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        j = i + 1
        extra: list[str] = []
        while j < len(lines) and not re.match(r"^[A-Za-z0-9_-]+:\s*", lines[j]):
            extra.append(lines[j])
            j += 1
        val = " ".join([val] + [e.strip() for e in extra]).strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
        i = j
    return fm


def collect_skills(skills_dir: Path = SKILLS) -> dict[str, dict]:
    skills: dict[str, dict] = {}
    if not skills_dir.is_dir():
        errors.append("skills/ missing")
        return skills
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"missing SKILL.md: skills/{entry.name}")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = fm.get("name", entry.name)
        desc = fm.get("description", "")
        hidden = str(fm.get("disable-model-invocation", "")).strip().lower() == "true"
        if name != entry.name:
            errors.append(f"name/folder mismatch: skills/{entry.name} name={name!r}")
        if name in skills:
            errors.append(f"duplicate skill name: {name}")
        skills[name] = {"path": str(skill_md), "desc": desc, "dir": entry.name,
                        "hidden": hidden}
    return skills


def check_essentials_inventory() -> None:
    """templates-inventory.md essentials list must match essentials/ on disk."""
    if not INVENTORY.is_file():
        return
    inv = INVENTORY.read_text(encoding="utf-8")
    m = re.search(r"## The essentials.*?(?=\n## |\Z)", inv, re.S)
    if not m:
        errors.append("templates-inventory.md missing 'The essentials' section")
        return
    claimed = set(re.findall(r"`([a-zA-Z0-9._-]+\.md)`", m.group(0)))
    on_disk = {p.name for p in ESSENTIALS.glob("*.md")}
    for name in sorted(claimed - on_disk):
        errors.append(f"inventory lists nonexistent essential: {name}")
    for name in sorted(on_disk - claimed):
        errors.append(f"essential not listed in templates-inventory.md: {name}")


def check_essentials() -> None:
    for ef in ESSENTIAL_FILES:
        if not (ESSENTIALS / ef).is_file():
            errors.append(f"missing essential doc: {ef}")
    readme_path = ESSENTIALS / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    for ef in ESSENTIAL_FILES:
        if ef != "README.md" and ef not in readme:
            errors.append(f"essential not indexed in README: {ef}")


def check_templates_inventory() -> None:
    if not INVENTORY.is_file():
        errors.append("missing references/templates-inventory.md")
        return
    inv = INVENTORY.read_text(encoding="utf-8")
    on_disk = sorted(
        p.name
        for p in TEMPLATES.iterdir()
        if p.is_file() and not p.name.startswith(".")
    )
    for name in on_disk:
        # source.yml is an inspo ledger template; inventory may list it or omit --
        # require every non-source template to be named in the inventory body.
        if name == "source.yml":
            continue
        if name not in inv:
            errors.append(f"template not listed in inventory: {name}")
    claimed = re.search(r"(\d+)\s+CLI-neutral format templates", inv)
    expected = len([n for n in on_disk if n != "source.yml"])
    if claimed:
        n = int(claimed.group(1))
        if n != expected:
            errors.append(
                f"templates inventory count {n} != on-disk format templates {expected} "
                f"(excluding source.yml)"
            )


def is_foundation(folder: str) -> bool:
    return folder.endswith("-foundation")




def check_visibility_policy(skills: dict[str, dict]) -> None:
    """Visibility follows invocation ownership, not leaf-vs-router shape."""
    for name, info in sorted(skills.items()):
        folder, hidden = info["dir"], info["hidden"]
        if is_foundation(folder) and not hidden and folder not in FOUNDATION_ALLOWLIST:
            errors.append(
                f"visible foundation (add disable-model-invocation: true or allowlist): {folder}"
            )
        if folder in ENTRY_SKILLS and hidden:
            errors.append(f"entry skill must stay model-visible: {folder}")
        if folder in INTERNAL_SKILLS and not hidden:
            errors.append(f"internal skill must stay hidden: {folder}")
        if not hidden and classify(folder, hidden) is None:
            errors.append(
                f"unclassified visible skill (add to ENTRY_SKILLS, ROUTER_SKILLS, or "
                f"VENDOR_SKILLS in catalog-quality.py, or hide it): {folder}"
            )


def budget_report(skills: dict[str, dict]) -> dict:
    visible = {n: i for n, i in skills.items() if not i["hidden"]}
    vis_chars = sum(len(n) + len(i["desc"]) for n, i in visible.items())
    classes: dict[str, list[str]] = {}
    unclassified_visible: list[str] = []
    for n, i in sorted(skills.items()):
        c = classify(i["dir"], i["hidden"])
        if c is None:
            if not i["hidden"]:
                unclassified_visible.append(n)
            continue
        classes.setdefault(c, []).append(n)
    largest = sorted(visible.items(), key=lambda kv: -len(kv[1]["desc"]))[:8]
    return {
        "total": len(skills),
        "visible": len(visible),
        "hidden": len(skills) - len(visible),
        "chars": vis_chars,
        "tokens": vis_chars // TOKEN_CHARS,
        "classes": {c: len(v) for c, v in sorted(classes.items())},
        "class_members": {c: sorted(v) for c, v in sorted(classes.items())},
        "unclassified_visible": sorted(unclassified_visible),
        "largest": largest,
    }


def print_budget(rep: dict) -> None:
    print("Skill catalog context budget")
    print(f"  Total skills:                 {rep['total']}")
    print(f"  Visible skills:               {rep['visible']}")
    print(f"  Hidden skills:                {rep['hidden']}")
    print("  Visible metadata:")
    print(f"    characters:                 {rep['chars']}")
    print(f"    estimated tokens (~{TOKEN_CHARS} c/tok, trend metric only): {rep['tokens']}")
    print("  Classification (entry / router / internal / cold / vendor):")
    for c in ("entry", "router", "internal", "cold", "vendor"):
        members = rep["class_members"].get(c, [])
        print(f"    {c:9} {len(members):4}  " + ", ".join(m for m in members if not is_foundation(m)))
    if rep["unclassified_visible"]:
        print("  UNCLASSIFIED VISIBLE (cleanup queue):")
        for n in rep["unclassified_visible"]:
            print(f"    - {n}")
    else:
        print("  unclassified visible:        0")
    print("  Largest visible descriptions:")
    for n, i in rep["largest"]:
        print(f"    {len(i['desc']):5d}  {n}")


def check_budget_baseline(rep: dict, default_root: bool) -> None:
    if not default_root:
        return
    for n, i in rep["largest"]:
        if len(i["desc"]) > DESC_WARN_CHARS:
            warnings.append(
                f"visible description {len(i['desc'])} chars > {DESC_WARN_CHARS}: {n} "
                f"(the body owns the workflow; keep the trigger short)"
            )
    if not BASELINE.is_file():
        warnings.append(
            "no context-budget baseline (scripts/context-budget-baseline.json); "
            "run catalog-quality.py --update-baseline after an intentional change"
        )
        return
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        base_chars = int(data["visible_chars"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"baseline unreadable: {exc}")
        return
    if rep["chars"] > base_chars:
        warnings.append(
            f"context budget grew: {rep['chars']} > baseline {base_chars} visible chars"
        )
    if rep["chars"] > base_chars * GROWTH_FAIL:
        errors.append(
            f"context budget {rep['chars']} exceeds baseline {base_chars} by more than "
            f"{int((GROWTH_FAIL - 1) * 100)}%; adding capabilities must not silently grow "
            f"startup context - update the baseline deliberately via --update-baseline"
        )


def near_duplicate_warnings(skills: dict[str, dict]) -> None:
    descs = [(n, i["desc"].lower()) for n, i in skills.items() if i["desc"]]
    for i in range(len(descs)):
        for j in range(i + 1, len(descs)):
            n1, d1 = descs[i]
            n2, d2 = descs[j]
            shorter = min(len(d1), len(d2))
            if shorter < 40:
                continue
            common = 0
            for k in range(min(shorter, 80)):
                if d1[k] == d2[k]:
                    common += 1
                else:
                    break
            if common > 0.7 * min(shorter, 80):
                warnings.append(f"near-duplicate descriptions: {n1} ~ {n2} (prefix {common} chars)")


def main() -> int:
    update_baseline = "--update-baseline" in sys.argv
    root_arg: str | None = None
    if "--root" in sys.argv:
        root_arg = sys.argv[sys.argv.index("--root") + 1]
    skills_dir = Path(root_arg) if root_arg else SKILLS
    default_root = skills_dir == SKILLS

    skills = collect_skills(skills_dir)
    if default_root:
        check_essentials()
        check_templates_inventory()
        check_essentials_inventory()
    near_duplicate_warnings(skills)
    check_visibility_policy(skills)
    rep = budget_report(skills)
    print_budget(rep)
    check_budget_baseline(rep, default_root)

    if errors:
        print("CATALOG QUALITY FAILURES:")
        for err in errors:
            print(f"  - {err}")
        return 1

    # Baseline updates are deliberate: never on an invalid catalog (review fix).
    if update_baseline and default_root and not errors:
        BASELINE.write_text(
            json.dumps({
                "visible_chars": rep["chars"],
                "visible_skills": rep["visible"],
                "updated": date.today().isoformat(),
                "note": "visible skill name+description chars; deliberate updates only",
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"baseline updated: {rep['chars']} visible chars, {rep['visible']} visible skills")
    print(f"CATALOG QUALITY OK: {len(skills)} skills, {len(ESSENTIAL_FILES)} essentials")
    for w in warnings[:40]:
        print(f"  (warn) {w}")
    if len(warnings) > 40:
        print(f"  (warn) ... {len(warnings)} total warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

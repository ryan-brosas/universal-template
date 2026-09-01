#!/usr/bin/env python3
# noinspection LSPLocalInspectionTool
"""Catalog quality gate: structure checks and the context-budget report.

These checks fail (exit 1) when:
- a skill directory lacks `SKILL.md`, the name does not match, or names repeat;
- the essentials are missing or not indexed in `essentials/README.md`;
- a required template is missing from `templates/`;
- a visible skill stays unclassified;
- visible metadata grows beyond the recorded baseline; a deliberate
  refresh with the update-baseline flag resets it.

Warnings print without failing.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set

BASE = Path(__file__).resolve().parents[1]
SKILLS = BASE / "skills"
ESSENTIALS = BASE / "essentials"
TEMPLATES = BASE / "templates"
BASELINE = BASE / "scripts" / "context-budget-baseline.json"

DESC_WARN_CHARS = 450      # visible description size worth reporting
GROWTH_FAIL = 1.10         # unexplained growth above baseline fails CI
TOKEN_CHARS = 4            # documented rough estimator; trend metric only

# Invocation-ownership classification (validator-side policy; hosts only read
# disable-model-invocation). Every visible skill must carry an explicit class:
# entry (a user request selects it directly), router (automatic dispatch point),
# or vendor (externally managed). Hidden skills are cold by default (searchable
# specialist knowledge) unless listed as internal (another skill/system invokes
# them).
ENTRY_SKILLS = {
    # flow entries
    "project-bootstrap", "brainstorming", "goal-setup", "prototype",
    "leverage-capture", "reference-driven-development",
    # GitHub / delivery
    "github-repo-setup", "github-actions-engineering", "push-pr",
    "git-workflow-and-versioning", "github-contribution-opportunities",
    # engineering procedures
    "coding-best-practices", "code-cleanup", "debugging-and-error-recovery",
    "test-generation", "security-and-hardening", "api-and-interface-design",
    "system-design-specification", "deprecation-and-migration",
    "improve-codebase-architecture", "farmed-test-harness", "grill-me",
    # authoring / prose gates
    "writing-skills", "house-writing-style", "copywriting",
    # discovery
    "skill-catalog",
    # tool / runtime capabilities (frequent-in-coding tools only; rare
    # utilities stay cold and searchable: `findata`, `gmaps`, `gnews`,
    # `rsearch`, `xsearch`, `ttdl`, `ytdl`, `gemini-large-context`)
    "cdp", "gsearch", "web-reference",
    "upwork-proposals", "omarchy", "math-schema",
    "mcp-steroid",
}
# Cold references formerly routed automatically; kept searchable, not hot.
ROUTER_SKILLS: set[str] = set()
# Internally invoked mechanics: never in model start-up metadata.
INTERNAL_SKILLS = {
    "model-resolution", "veda-lane", "fabric-native-execution",
    "evidence-router", "execution-router",
    "code-discipline", "agent-code-quality-gate",
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


def classify(folder: str, hidden: bool) -> Optional[str]:
    """Mechanical class for a skill (None = unclassified)."""
    if folder in VENDOR_SKILLS:
        return "vendor"
    if not hidden:
        if folder in ROUTER_SKILLS:
            return "router"
        if folder in ENTRY_SKILLS:
            return "entry"
        return None
    return "internal" if folder in INTERNAL_SKILLS else "cold"

errors: List[str] = []
warnings: List[str] = []

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

# Active skill and documentation consumers depend on these templates. This is
# a required-file contract, not a hand-maintained inventory: templates/ remains
# the authoritative source for the files and their contents.
REQUIRED_TEMPLATE_FILES = (
    "agents.md",
    "project-context.md",
    "roadmap.md",
    "readme.md",
    "pull-request.md",
    "github-pr-ci.yml",
    "skill.md",
)


def template_errors(templates_dir: Path) -> List[str]:
    return [
        f"missing required template: templates/{name}"
        for name in REQUIRED_TEMPLATE_FILES
        if not (templates_dir / name).is_file()
    ]


def check_templates(templates_dir: Path = TEMPLATES) -> None:
    errors.extend(template_errors(templates_dir))


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[4:end] if text.startswith("---\n") else text[3:end]
    fm: Dict[str, str] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        j = i + 1
        extra: List[str] = []
        while j < len(lines) and not re.match(r"^[A-Za-z0-9_-]+:\s*", lines[j]):
            extra.append(lines[j])
            j += 1
        val = " ".join([val] + [e.strip() for e in extra]).strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
        i = j
    return fm


def git_ignored_dirs(root: Path) -> Set[str]:
    """Skill directories ignored by git on this machine (machine-local skills).

    The budget, the baseline, and the generated catalogs must all measure the
    tracked set: a clean CI checkout has to reproduce every number. Local
    search (skill-catalog list/search) still lists machine-local skills.
    """
    try:
        import subprocess
        dirs = [d.name for d in root.iterdir()
                if d.is_dir() and not d.name.startswith(".")]
        r = subprocess.run(
            ["git", "-C", str(root.parent), "check-ignore", "--stdin", "--no-index"],
            input="\n".join("skills/" + n for n in dirs) + "\n",
            capture_output=True, text=True)
        if r.returncode not in (0, 1):
            return set()
        return {line.rsplit("/", 1)[-1] for line in r.stdout.splitlines() if line.strip()}
    except Exception:  # noqa: BLE001 - no git available: treat everything as tracked
        return set()


def collect_skills(skills_dir: Path = SKILLS) -> Dict[str, dict]:
    skills: Dict[str, dict] = {}
    if not skills_dir.is_dir():
        errors.append("skills/ missing")
        return skills
    ignored = git_ignored_dirs(skills_dir)
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in ignored:
            continue  # machine-local skill: tracked-set metrics only
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


def check_essentials() -> None:
    for ef in ESSENTIAL_FILES:
        if not (ESSENTIALS / ef).is_file():
            errors.append(f"missing essential doc: {ef}")
    readme_path = ESSENTIALS / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    for ef in ESSENTIAL_FILES:
        if ef != "README.md" and ef not in readme:
            errors.append(f"essential not indexed in README: {ef}")


def check_visibility_policy(skills: Dict[str, dict]) -> None:
    """Visibility follows invocation ownership, not leaf-vs-router shape."""
    for name, info in sorted(skills.items()):
        folder, hidden = info["dir"], info["hidden"]
        if folder in ENTRY_SKILLS and hidden:
            errors.append(f"entry skill must stay model-visible: {folder}")
        if folder in INTERNAL_SKILLS and not hidden:
            errors.append(f"internal skill must stay hidden: {folder}")
        if not hidden and classify(folder, hidden) is None:
            errors.append(
                f"unclassified visible skill (add to ENTRY_SKILLS, ROUTER_SKILLS, or "
                f"VENDOR_SKILLS in catalog-quality.py, or hide it): {folder}"
            )


def budget_report(skills: Dict[str, dict]) -> dict:
    visible = {n: i for n, i in skills.items() if not i["hidden"]}
    vis_chars = sum(len(n) + len(i["desc"]) for n, i in visible.items())
    classes: Dict[str, List[str]] = {}
    unclassified_visible: List[str] = []
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
        print(f"    {c:9} {len(members):4}  " + ", ".join(members))
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


def near_duplicate_warnings(skills: Dict[str, dict]) -> None:
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


def check_generated_catalogs() -> None:
    """The generated `docs/skill-catalog.md` must be current.

    Generated views are derived from `skills/*/SKILL.md` plus `classify()`; they are
    validated here so catalog-quality is the one required catalog gate.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "skill_catalog", str(Path(__file__).with_name("skill-catalog.py")))
    if spec is None or spec.loader is None:
        errors.append("cannot load scripts/skill-catalog.py")
        return
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        targets = mod.build_docs(mod.scan())
    except Exception as exc:  # noqa: BLE001 - broken generator is a normal failure
        errors.append(
            f"cannot generate catalogs ({type(exc).__name__}: {exc}); "
            f"restore scripts/skill-catalog.py and rerun")
        return
    for rel, content in targets.items():
        p = BASE / rel
        if not p.is_file() or p.read_text(encoding="utf-8") != content:
            errors.append(
                f"generated catalog stale: {rel} "
                f"(rerun python3 scripts/skill-catalog.py generate)")


def selftest_templates() -> int:
    """The gate rejects a required template that is removed or renamed."""
    with tempfile.TemporaryDirectory(prefix="catalog-quality-") as tmp:
        fixture = Path(tmp)
        for name in REQUIRED_TEMPLATE_FILES:
            (fixture / name).write_text("fixture\n", encoding="utf-8")
        if template_errors(fixture):
            print("catalog-quality selftest: FAIL (complete fixture rejected)")
            return 1

        required = fixture / REQUIRED_TEMPLATE_FILES[0]
        required.rename(fixture / f"{required.stem}-renamed{required.suffix}")
        expected = f"missing required template: templates/{REQUIRED_TEMPLATE_FILES[0]}"
        failures = template_errors(fixture)
        if expected not in failures:
            print("catalog-quality selftest: FAIL (renamed template accepted)")
            return 1
    print("catalog-quality selftest: PASS")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest_templates()
    update_baseline = "--update-baseline" in sys.argv
    root_arg: Optional[str] = None
    if "--root" in sys.argv:
        root_arg = sys.argv[sys.argv.index("--root") + 1]
    skills_dir = Path(root_arg) if root_arg else SKILLS
    default_root = skills_dir == SKILLS

    skills = collect_skills(skills_dir)
    if default_root:
        check_essentials()
        check_templates()
        check_generated_catalogs()
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
